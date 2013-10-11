# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium_android',
  'properties',
  'json',
]

def GenSteps(api):
  droid = api.chromium_android
  yield droid.common_tree_setup_steps()
  if droid.c.apply_svn_patch:
    yield droid.apply_svn_patch()
  yield droid.download_build()
  yield droid.common_tests_setup_steps()
  yield droid.instrumentation_tests()
  yield droid.common_tests_final_steps()

def GenTests(api):
  bot_ids = ['main_tests', 'enormous_tests', 'try_instrumentation_tests',
             'x86_try_instrumentation_tests']

  def common_test_data(props):
    return (
        props +
        api.step_data(
          'get app_manifest_vars',
          api.json.output({
            'version_code': 10,
            'version_name': 'some_builder_1234',
            'build_id': 3333,
            'date_string': 6001
          })
        ) +
        api.step_data(
          'envsetup',
          api.json.output({
            'PATH': './',
            'GYP_DEFINES': 'my_new_gyp_def=aaa',
            'GYP_SOMETHING': 'gyp_something_value'
          })
        )
    )

  def props(bot_id):
    return api.properties(
      repo_name='src/repo',
      repo_url='svn://svn.chromium.org/chrome/trunk/src',
      revision='4f4b02f6b7fa20a3a25682c457bbc8ad589c8a00',
      android_bot_id=bot_id,
      buildername='test_buildername',
      parent_buildername='parent_buildername',
      internal=True
    )

  for bot_id in bot_ids:
    p = props(bot_id)
    if 'try_instrumentation_tests' in bot_id:
      p += api.properties(revision='')
      p += api.properties(parent_buildnumber=1357)
      p += api.properties(patch_url='try_job_svn_patch')

    yield api.test(bot_id) + common_test_data(p)

  # failure tests
  yield (api.test('main_tests_device_status_check_fail') +
         common_test_data(props('main_tests')) +
         api.step_data('device_status_check', retcode=1))
  yield (api.test('main_tests_deploy_fail') +
         common_test_data(props('main_tests')) +
         api.step_data('deploy_on_devices', retcode=1))
  yield (api.test('main_tests_provision_fail') +
         common_test_data(props('main_tests')) +
         api.step_data('provision_devices', retcode=1))
