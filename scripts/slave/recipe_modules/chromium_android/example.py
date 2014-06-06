# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'adb',
    'chromium_android',
    'json',
    'properties',
]

BUILDERS = {
    'basic_builder': {
        'target': 'Release',
        'build': True,
    },
    'restart_usb_builder': {
        'restart_usb': True,
        'target': 'Release',
        'build': True,
    },
    'coverage_builder': {
        'coverage': True,
        'target': 'Debug',
        'build': True,
    },
    'tester': {
        'build': False,
    }
}

def GenSteps(api):
  config = BUILDERS[api.properties['buildername']]

  api.chromium_android.configure_from_properties(
      'base_config',
      INTERNAL=True,
      BUILD_CONFIG='Release')

  api.chromium_android.c.get_app_manifest_vars = True
  api.chromium_android.c.coverage = config.get('coverage', False)
  api.chromium_android.c.asan_symbolize = True

  yield api.chromium_android.init_and_sync()

  yield api.chromium_android.envsetup()
  yield api.chromium_android.runhooks()
  yield api.chromium_android.apply_svn_patch()
  yield api.chromium_android.run_tree_truth()
  if config['build']:
    yield api.chromium_android.compile()
  else:
    yield api.chromium_android.download_build('build-bucket',
                                              'build_product.zip')
  yield api.chromium_android.git_number()

  yield api.adb.root_devices()
  yield api.chromium_android.spawn_logcat_monitor()
  yield api.chromium_android.device_status_check(
      restart_usb=config.get('restart_usb', False))

  yield api.chromium_android.monkey_test()
  yield api.chromium_android.run_sharded_perf_tests(
      config='fake_config.json',
      flaky_config='flake_fakes.json')
  yield api.chromium_android.run_instrumentation_suite(
      test_apk='AndroidWebViewTest',
      test_data='webview:android_webview/test/data/device_files',
      flakiness_dashboard='test-results.appspot.com',
      annotation='SmallTest',
      except_annotation='FlakyTest',
      screenshot=True)
  yield api.chromium_android.run_test_suite('unittests')
  yield api.chromium_android.run_bisect_script(extra_src='test.py',
                                               path_to_config='test.py')

  yield api.chromium_android.logcat_dump()
  yield api.chromium_android.stack_tool_steps()
  if config.get('coverage', False):
    yield api.chromium_android.coverage_report()
  yield api.chromium_android.cleanup_build()

def GenTests(api):
  def properties_for(buildername):
    return api.properties.generic(
        buildername=buildername,
        slavename='tehslave',
        repo_name='src/repo',
        patch_url='https://the.patch.url/the.patch',
        repo_url='svn://svn.chromium.org/chrome/trunk/src',
        revision='4f4b02f6b7fa20a3a25682c457bbc8ad589c8a00',
        internal=True)

  for buildername in BUILDERS:
    yield api.test('%s_basic' % buildername) + properties_for(buildername)

  yield (api.test('tester_no_devices') +
         properties_for('tester') +
         api.step_data('device_status_check', retcode=1))
