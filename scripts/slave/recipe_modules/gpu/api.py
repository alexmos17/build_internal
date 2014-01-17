# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api

SIMPLE_TESTS_TO_RUN = [
  'content_gl_tests',
  'gles2_conform_test',
  'angle_unittests'
]

class GpuApi(recipe_api.RecipeApi):
  def setup(self):
    """Call this once before any of the other APIs in this module."""

    # These values may be replaced by external configuration later
    self._dashboard_upload_url = 'https://chromeperf.appspot.com'
    self._gs_bucket_name = 'chromium-gpu-archive'

    # The infrastructure team has recommended not to use git yet on the
    # bots, but it's useful -- even necessary -- when testing locally.
    # To use, pass "use_git=True" as an argument to run_recipe.py.
    self._use_git = self.m.properties.get('use_git', False)

    # TODO(kbr): currently the pixel and maps tests use the build revision
    # (which is assumed to be the SVN revision of src/) when uploading
    # error images to cloud storage, only for naming purposes. This should
    # be changed to use a different identifier, for example, the build
    # number on the slave. For now, pass down the intended value. Note that
    # this is overridden below using the correct values from gclient. This
    # is here in order to still support commenting out the block of code
    # below while testing locally.
    self._build_revision = self.m.properties['revision']

    self._configuration = 'chromium'
    if self.m.gclient.is_blink_mode:
      self._configuration = 'blink'

    self.m.chromium.set_config(self._configuration, GIT_MODE=self._use_git)
    # This is needed to make GOMA work properly on Mac.
    if self.m.platform.is_mac:
      self.m.chromium.set_config(self._configuration + '_clang',
                                 GIT_MODE=self._use_git)
    self.m.gclient.apply_config('chrome_internal')

    # Use the default Ash and Aura settings on all bots (specifically Blink bots).
    self.m.chromium.c.gyp_env.GYP_DEFINES.pop('use_ash', None)
    self.m.chromium.c.gyp_env.GYP_DEFINES.pop('use_aura', None)

    # TODO(kbr): remove the workaround for http://crbug.com/328249 .
    self.m.chromium.c.gyp_env.GYP_DEFINES['disable_glibcxx_debug'] = 1

    # Don't skip the frame_rate data, as it's needed for the frame rate tests.
    # Per iannucci@, it can be relied upon that solutions[1] is src-internal.
    # Consider managing this in a 'gpu' config.
    del self.m.gclient.c.solutions[1].custom_deps[
        'src/chrome/test/data/perf/frame_rate/private']

    self.m.chromium.c.gyp_env.GYP_DEFINES['internal_gles2_conform_tests'] = 1

    # Isolates don't work with the component build yet.
    # Fortunately, we can easily tell which GPU bots are using the
    # component build -- all of those building or testing Debug.
    self._use_isolates = self.m.chromium.is_release_build
    if self._use_isolates:
      self.m.isolate.set_isolate_environment(self.m.chromium.c)

  def checkout_steps(self):
    # Always force a gclient-revert in order to avoid problems when
    # directories are added to, removed from, and re-added to the repo.
    # crbug.com/329577
    yield self.m.gclient.checkout(revert=True)
    gclient_data = self.m.step_history['gclient sync'].json.output
    self._build_revision = gclient_data['solutions']['src/']['revision']
    # If being run as a try server, apply the CL.
    if 'rietveld' in self.m.properties:
      yield self.m.rietveld.apply_issue(self.m.rietveld.calculate_issue_root())

  def compile_steps(self):
    # We only need to runhooks if we're going to compile locally.
    yield self.m.chromium.runhooks()
    # Since performance tests aren't run on the debug builders, it isn't
    # necessary to build all of the targets there.
    build_tag = '' if self.m.chromium.is_release_build else 'debug_'
    # It's harmless to process the isolate-related targets even if they
    # aren't supported on the current configuration (because the component
    # build is used).
    yield self.m.chromium.compile(
        targets=['chromium_gpu_%sbuilder' % build_tag, 'gl_tests_run'])
    # This is only an initial test of the isolate upload path; the
    # subsequent GPU isolates will follow.
    yield self.m.isolate.manifest_to_hash(['gl_tests'])

  def upload_steps(self):
    yield self.m.archive.zip_and_upload_build(
      'package_build',
      self.m.chromium.c.build_config_fs,
      self.m.chromium.c.build_dir,
      self.m.archive.legacy_upload_url(
        self._gs_bucket_name,
        extra_url_components=self.m.properties['mastername']))

  def download_steps(self):
    yield self.m.archive.download_and_unzip_build(
      'extract_build',
      self.m.chromium.c.build_config_fs,
      self.m.chromium.c.build_dir,
      self.m.archive.legacy_download_url(
        self._gs_bucket_name,
        extra_url_components=self.m.properties['mastername']))

  def test_steps(self):
    # TODO(kbr): currently some properties are passed to runtest.py via
    # factory_properties in the master.cfg: generate_gtest_json,
    # show_perf_results, test_results_server, and perf_id. runtest.py
    # should be modified to take these arguments on the command line,
    # and the setting of these properties should happen in this recipe
    # instead.

    # On Windows, start the crash service.
    if self.m.platform.is_win:
      yield self.m.python(
        'start_crash_service',
        self.m.path.build('scripts', 'slave', 'chromium',
                          'run_crash_handler.py'),
        ['--build-dir',
         self.m.chromium.c.build_dir,
         '--target',
         self.m.chromium.c.build_config_fs])

    # Note: --no-xvfb is the default.
    for test in SIMPLE_TESTS_TO_RUN:
      yield self.m.chromium.runtests(test)

    if self._use_isolates:
      yield self.m.isolate.run_isolate_test('gl_tests')
    else:
      yield self.m.chromium.runtests('gl_tests')

    # Choose a reasonable default for the location of the sandbox binary
    # on the bots.
    env = {}
    if self.m.platform.is_linux:
      env['CHROME_DEVEL_SANDBOX'] = '/opt/chromium/chrome_sandbox'

    # Google Maps Pixel tests.
    yield self.run_telemetry_gpu_test('maps', name='maps_pixel_test',
        args=[
            '--build-revision',
            str(self._build_revision),
            '--test-machine-name',
            self.m.properties['buildername']
        ])

    # Pixel tests.
    # Try servers pull their results from cloud storage; the other
    # tester bots send their results to cloud storage.
    #
    # NOTE that ALL of the bots need to share a bucket. They can't be split
    # by mastername/waterfall, because the try servers are on a different
    # waterfall (tryserver.chromium) than the other test bots (chromium.gpu
    # and chromium.webkit, as of this writing). This means there will be
    # races between bots with identical OS/GPU combinations, on different
    # waterfalls, attempting to upload results for new versions of each
    # pixel test. If this is a significant problem in practice then we will
    # have to rethink the cloud storage code in the pixel tests.
    ref_img_arg = '--upload-refimg-to-cloud-storage'
    if 'rietveld' in self.m.properties:
      ref_img_arg = '--download-refimg-from-cloud-storage'
    cloud_storage_bucket = 'chromium-gpu-archive/reference-images'
    yield self.run_telemetry_gpu_test('pixel_test',
        args=[
            '--build-revision',
            str(self._build_revision),
            ref_img_arg,
            '--refimg-cloud-storage-bucket',
            cloud_storage_bucket,
            '--os-type',
            self.m.chromium.c.TARGET_PLATFORM,
            '--test-machine-name',
            self.m.properties['buildername']
        ])

    # WebGL conformance tests.
    yield self.run_telemetry_gpu_test('webgl_conformance',
        args=[
            '--webgl-conformance-version=1.0.2'
        ])

    # Context lost tests.
    yield self.run_telemetry_gpu_test('context_lost')

    # Memory tests.
    yield self.run_telemetry_gpu_test('memory_test')

    # Hardware acceleration tests.
    yield self.run_telemetry_gpu_test('hardware_accelerated_feature')

    # GPU process launch tests.
    yield self.run_telemetry_gpu_test('gpu_process', name='gpu_process_launch')

    # Only run the performance tests on Release builds.
    if self.m.chromium.is_release_build:
      # Former tab_capture_performance_tests_step
      args = ['--enable-gpu',
              '--test-launcher-jobs=1',
              '--test-launcher-print-test-stdio=always',
              '--gtest_filter=TabCapturePerformanceTest*']
      yield self.m.chromium.runtests('performance_browser_tests',
                                     args,
                                     name='tab_capture_performance_tests',
                                     annotate='graphing',
                                     results_url=self._dashboard_upload_url,
                                     perf_dashboard_id='tab_capture_performance',
                                     test_type='tab_capture_performance_tests',
                                     spawn_dbus=True)

    # TODO(kbr): after the conversion to recipes, add all GPU related
    # steps from the main waterfall, like gpu_unittests.

    # On Windows, process any crash dumps that may have occurred.
    if self.m.platform.is_win:
      yield self.m.python(
        'process_dumps',
        self.m.path.build('scripts', 'slave', 'process_dumps.py'),
        ['--build-dir',
         self.m.chromium.c.build_dir,
         '--target',
         self.m.chromium.c.build_config_fs])

  def run_telemetry_gpu_test(self, test, name='', args=None,
                             results_directory=''):
    """Returns a step which runs a Telemetry based GPU test (via
    run_gpu_test)."""

    test_args = ['-v']
    if args:
      test_args.extend(args)

    return self.m.chromium.run_telemetry_test(
        str(self.m.path.checkout('content', 'test', 'gpu', 'run_gpu_test')),
        test, name, test_args, results_directory, spawn_dbus=True)
