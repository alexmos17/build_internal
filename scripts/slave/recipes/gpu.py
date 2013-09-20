# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# This recipe is intended to control all of the GPU related bots:
#   chromium.gpu
#   chromium.gpu.fyi
#   The GPU bots on the chromium.webkit waterfall
#   The GPU bots on the tryserver.chromium waterfall

DEPS = [
  'chromium',
  'gclient',
  'path',
  'properties',
  'rietveld',
]

SIMPLE_TESTS_TO_RUN = [
  'content_gl_tests',
  'gles2_conform_test',
  'gl_tests'
]

def GenSteps(api):
  # These values may be replaced by external configuration later
  dashboard_upload_url = 'https://chromeperf.appspot.com'
  generated_dir = api.path.slave_build('content_gpu_data', 'generated')
  reference_dir = api.path.slave_build('content_gpu_data', 'reference')

  api.chromium.set_config('chromium')
  api.gclient.apply_config('chrome_internal')

  # Don't skip the frame_rate data, as it's needed for the frame rate tests.
  # Per iannucci@, it can be relied upon that solutions[1] is src-internal.
  # Consider adding a 'gpu' module so that this can be managed in a
  # 'gpu' config.
  del api.gclient.c.solutions[1].custom_deps[
    'src/chrome/test/data/perf/frame_rate/private']

  api.chromium.c.gyp_env.GYP_DEFINES['internal_gles2_conform_tests'] = 1

  # If you want to stub out the checkout/runhooks/compile steps,
  # uncomment this line and then comment out the associated block of
  # yield statements below.
  # api.path.add_checkout(api.path.slave_build('src'))

  yield api.gclient.checkout()
  # If being run as a try server, apply the CL.
  if 'rietveld' in api.properties:
    yield api.rietveld.apply_issue()
  yield api.chromium.runhooks()
  yield api.chromium.compile(targets=['chromium_gpu_builder'])

  # TODO(kbr): currently some properties are passed to runtest.py via
  # factory_properties in the master.cfg: generate_gtest_json,
  # show_perf_results, test_results_server, and perf_id. runtest.py
  # should be modified to take these arguments on the command line,
  # and the setting of these properties should happen in this recipe
  # instead.

  # Note: --no-xvfb is the default.
  for test in SIMPLE_TESTS_TO_RUN:
    yield api.chromium.runtests(test)

  # Former gpu_content_tests step
  args = ['--use-gpu-in-tests',
          '--generated-dir=%s' % generated_dir,
          '--reference-dir=%s' % reference_dir,
          '--build-revision=%s' % api.properties['revision'],
          '--gtest_filter=WebGLConformanceTest.*:Gpu*.*',
          '--ui-test-action-max-timeout=45000',
          '--run-manual']
  yield api.chromium.runtests('content_browsertests',
                              args,
                              annotate='gtest',
                              test_type='content_browsertests',
                              generate_json_file=True,
                              results_directory=
                                  'gtest-results/content_browsertests',
                              build_number=api.properties['buildnumber'],
                              builder_name=api.properties['buildername'])

  # Only run the performance tests on Release builds.
  if api.properties.get('build_config', 'Release') == 'Release':
    # Former gpu_frame_rate_test step
    args = ['--enable-gpu',
            '--gtest_filter=FrameRate*Test*']
    yield api.chromium.runtests('performance_ui_tests',
                                args,
                                name='gpu_frame_rate_test',
                                annotate='framerate',
                                results_url=dashboard_upload_url,
                                perf_dashboard_id='gpu_frame_rate',
                                test_type='gpu_frame_rate_test')

    # Former gpu_throughput_tests step
    args = ['--enable-gpu',
            '--gtest_filter=ThroughputTest*']
    yield api.chromium.runtests('performance_browser_tests',
                                args,
                                name='gpu_throughput_tests',
                                annotate='graphing',
                                results_url=dashboard_upload_url,
                                perf_dashboard_id='gpu_throughput',
                                test_type='gpu_throughput_tests')

    # Former tab_capture_performance_tests_step
    args = ['--enable-gpu',
            '--gtest_filter=TabCapturePerformanceTest*']
    yield api.chromium.runtests('performance_browser_tests',
                                args,
                                name='tab_capture_performance_tests',
                                annotate='graphing',
                                results_url=dashboard_upload_url,
                                perf_dashboard_id='tab_capture_performance',
                                test_type='tab_capture_performance_tests')

  # TODO(kbr): after the conversion to recipes, add all GPU related
  # steps from the main waterfall, like gpu_unittests.

def GenTests(api):
  for build_config in ['Release', 'Debug']:
    for plat in ['win', 'mac', 'linux']:
      # Normal builder configuration
      base_name = '%s_%s' % (plat, build_config.lower())
      yield base_name, {
        'properties': api.properties_scheduled(
          build_config=build_config),
        'mock': {
          'platform': {
            'name': plat
          }
        }
      }

      # Try server configuration
      yield '%s_tryserver' % base_name, {
        'properties': api.properties_tryserver(
          build_config=build_config),
        'mock': {
          'platform': {
            'name': plat
          }
        }
      }
