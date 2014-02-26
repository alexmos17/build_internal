# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'adb',
    'chromium_android',
    'json',
    'properties',
]

def GenSteps(api):
  api.chromium_android.configure_from_properties('base_config', INTERNAL=True)
  api.chromium_android.c.get_app_manifest_vars = True
  api.chromium_android.c.run_stack_tool_steps = True

  yield api.chromium_android.init_and_sync()

  version_name = api.chromium_android.version_name
  assert isinstance(version_name, basestring) and version_name, (
      'Could not get a valid version name.')

  yield api.chromium_android.envsetup()
  yield api.chromium_android.runhooks()
  yield api.chromium_android.compile()

  yield api.adb.root_devices()
  yield api.chromium_android.spawn_logcat_monitor()
  yield api.chromium_android.device_status_check()

  yield api.chromium_android.monkey_test()

  yield api.chromium_android.logcat_dump()
  yield api.chromium_android.stack_tool_steps()
  yield api.chromium_android.cleanup_build()

def GenTests(api):
  yield (
      api.test('basic') +
      api.properties(
        buildername='tehbuilder',
        repo_name='src/repo',
        repo_url='svn://svn.chromium.org/chrome/trunk/src',
        revision='4f4b02f6b7fa20a3a25682c457bbc8ad589c8a00',
        internal=True,
      ) +
      api.chromium_android.default_step_data(api))
