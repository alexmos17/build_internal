# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api
from slave.recipe_modules.webrtc import builders


class WebRTCApi(recipe_api.RecipeApi):
  def __init__(self, **kwargs):
    super(WebRTCApi, self).__init__(**kwargs)
    self._env = {}

  BUILDERS = builders.BUILDERS
  RECIPE_CONFIGS = builders.RECIPE_CONFIGS

  COMMON_TESTS = [
      'audio_decoder_unittests',
      'common_audio_unittests',
      'common_video_unittests',
      'modules_tests',
      'modules_unittests',
      'system_wrappers_unittests',
      'test_support_unittests',
      'tools_unittests',
      'video_engine_core_unittests',
      'voice_engine_unittests',
  ]

  ANDROID_APK_TESTS = COMMON_TESTS

  NORMAL_TESTS = sorted(COMMON_TESTS + [
    'libjingle_media_unittest',
    'libjingle_p2p_unittest',
    'libjingle_peerconnection_unittest',
    'libjingle_sound_unittest',
    'libjingle_unittest',
    'video_engine_tests',
  ])

  # Map of GS archive names to urls.
  # TODO(kjellander): Convert to use the auto-generated URLs once we've setup a
  # separate bucket per master.
  GS_ARCHIVES = {
    'android_dbg_archive': 'gs://chromium-webrtc/android_chromium_dbg',
    'android_dbg_archive_fyi': ('gs://chromium-webrtc/'
                                'android_chromium_trunk_dbg'),
    'win_rel_archive': 'gs://chromium-webrtc/Win Builder',
    'win_rel_archive_fyi': 'gs://chromium-webrtc/win_rel-fyi',
    'mac_rel_archive': 'gs://chromium-webrtc/Mac Builder',
    'linux_rel_archive': 'gs://chromium-webrtc/Linux Builder',
  }

  DASHBOARD_UPLOAD_URL = 'https://chromeperf.appspot.com'

  def runtests(self, test_suite=None, revision=None):
    """Generate a list of tests to run.

    Args:
      test_suite: The name of the test suite.
      revision: Revision for the build. Mandatory for perf measuring tests.
    """
    steps = []
    if test_suite == 'webrtc':
      for test in self.NORMAL_TESTS:
        steps.append(self.add_test(test))

      if self.m.platform.is_mac and self.m.chromium.c.TARGET_BITS == 64:
        test = self.m.path.join('libjingle_peerconnection_objc_test.app',
                                'Contents', 'MacOS',
                                'libjingle_peerconnection_objc_test')
        steps.append(self.add_test(test,
                                   name='libjingle_peerconnection_objc_test'))
    elif test_suite == 'webrtc_baremetal':
      # Add baremetal tests, which are different depending on the platform.
      if self.m.platform.is_win or self.m.platform.is_mac:
        steps.append(self.add_test('audio_device_tests'))
      elif self.m.platform.is_linux:
        f = self.m.path['checkout'].join
        steps.append(self.add_test(
            'audioproc', name='audioproc_perf',
            args=['-aecm', '-ns', '-agc', '--fixed_digital', '--perf', '-pb',
                  f('resources', 'audioproc.aecdump')],
            revision=revision,
            perf_test=True))
        steps.append(self.add_test(
            'iSACFixtest', name='isac_fixed_perf',
            args=['32000', f('resources', 'speech_and_misc_wb.pcm'),
                  'isac_speech_and_misc_wb.pcm'],
            revision=revision,
            perf_test=True))
        steps.append(self.virtual_webcam_check())
        steps.append(self.add_test(
            'libjingle_peerconnection_java_unittest',
            env={'LD_PRELOAD': '/usr/lib/x86_64-linux-gnu/libpulse.so.0'}))

      steps.append(self.virtual_webcam_check())
      steps.append(self.add_test('vie_auto_test',
          args=['--automated',
                '--capture_test_ensure_resolution_alignment_in_capture_device='
                'false']))
      steps.append(self.add_test('voe_auto_test', args=['--automated']))
      steps.append(self.virtual_webcam_check())
      steps.append(self.add_test('video_capture_tests'))
      steps.append(self.add_test('webrtc_perf_tests', revision=revision,
                                 perf_test=True))
    elif test_suite == 'chromium':
      # Many of these tests run in the Chromium WebRTC waterfalls are not run in
      # the main Chromium waterfalls as they are marked as MANUAL_. This is
      # because they rely on physical audio and video devices, which are only
      # available at bare-metal machines.
      steps.append(self.add_test(
          test='content_browsertests', name='content_browsertests (webrtc)',
          args=['--gtest_filter=WebRtc*', '--run-manual',
                '--test-launcher-print-test-stdio=always'],
          revision=revision,
          perf_test=True))
      steps.append(self.add_test(
          test='browser_tests', name='browser_tests (webrtc)',
          # These tests needs --test-launcher-jobs=1 since some of them are
          # not able to run in parallel (due to the usage of the
          # peerconnection server).
          args = ['--gtest_filter=WebRtc*',
                  '--run-manual', '--ui-test-action-max-timeout=300000',
                  '--test-launcher-jobs=1',
                  '--test-launcher-print-test-stdio=always'],
          revision=revision,
          perf_test=True))
      steps.append(self.add_test(
          test='content_unittests', name='content_unittests (webrtc)',
          args=['--gtest_filter=WebRTC*:RTC*:MediaStream*']))

      if self.m.properties['mastername'].endswith('chromium.webrtc.fyi'):
        steps.append(self.add_test('sizes'))

    return steps

  def add_test(self, test, name=None, args=None, revision=None, env=None,
               perf_test=False):
    args = args or []
    env = env or {}

    if self.c.PERF_ID and perf_test:
      assert revision, ('Revision must be specified for perf tests as they '
                        'upload data to the perf dashboard.')
      return self.m.chromium.runtest(
          test=test, args=args, name=name,
          results_url=self.DASHBOARD_UPLOAD_URL, annotate='graphing',
          xvfb=True, perf_dashboard_id=test, test_type=test, env=env,
          revision=revision, perf_id=self.c.PERF_ID,
          perf_config=self.c.PERF_CONFIG)
    else:
      return self.m.chromium.runtest(
          test=test, args=args, name=name, annotate='gtest', xvfb=True,
              test_type=test, env=env)

  def package_build(self, gs_url, revision):
    yield self.m.archive.zip_and_upload_build(
        'package build',
        self.m.chromium.c.build_config_fs,
        gs_url,
        build_revision=revision)

  def extract_build(self, gs_url, revision):
    yield self.m.archive.download_and_unzip_build(
        'extract build',
        self.m.chromium.c.build_config_fs,
        gs_url,
        build_revision=revision,
        abort_on_failure=True)

  def apply_svn_patch(self):
    script = self.m.path['build'].join('scripts', 'slave', 'apply_svn_patch.py')
    # Use the SVN mirror as the slaves only have authentication setup for that.
    patch_url = self.m.properties['patch_url'].replace(
        'svn://svn.chromium.org', 'svn://svn-mirror.golo.chromium.org')
    args = ['-p', patch_url,
            '-r', self.c.patch_root_dir]

    # Allow manipulating patches for try jobs.
    if self.c.patch_filter_script and self.c.patch_path_filter:
      args += ['--filter-script', self.c.patch_filter_script,
               '--strip-level', self.c.patch_strip_level,
               '--', '--path-filter', self.c.patch_path_filter]
    return self.m.python('apply_patch', script, args)

  def virtual_webcam_check(self):
    return self.m.python(
      'webcam_check',
      self.m.path['build'].join('scripts', 'slave', 'webrtc',
                                'ensure_webcam_is_running.py'))
