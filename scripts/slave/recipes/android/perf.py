# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'bot_update',
    'chromium_android',
    'gclient',
    'step',
    'path',
    'properties',
]

REPO_URL = 'https://chromium.googlesource.com/chromium/src.git'

BUILDERS = {
  'android_nexus5_oilpan_perf': {
    'perf_id': 'android-nexus5-oilpan',
    'bucket': 'chromium-android',
    'path': lambda api: (
      '%s/build_product_%s.zip' % (
            api.properties['parent_buildername'],
            api.properties['parent_revision'])),
  },
  'Android Nexus4 Perf': {
    'perf_id': 'android-nexus4',
    'bucket': 'chrome-perf',
    'path': lambda api: ('android_perf_rel/full-build-linux_%s.zip'
                               % api.properties['parent_revision']),
  },
  'Android Nexus5 Perf': {
    'perf_id': 'android-nexus5',
    'bucket': 'chrome-perf',
    'path': lambda api: ('android_perf_rel/full-build-linux_%s.zip'
                               % api.properties['parent_revision']),
  },
  'Android Nexus7v2 Perf': {
    'perf_id': 'android-nexus7v2',
    'bucket': 'chrome-perf',
    'path': lambda api: ('android_perf_rel/full-build-linux_%s.zip'
                               % api.properties['parent_revision']),
  },
  'Android Nexus10 Perf': {
    'perf_id': 'android-nexus10',
    'bucket': 'chrome-perf',
    'path': lambda api: ('android_perf_rel/full-build-linux_%s.zip'
                               % api.properties['parent_revision']),
  },
  'Android GN Perf': {
    'perf_id': 'android-gn',
    'bucket': 'chrome-perf',
    'path': lambda api: ('android_perf_rel/full-build-linux_%s.zip'
                               % api.properties['parent_revision']),
  },
}

def GenSteps(api):
  buildername = api.properties['buildername']
  builder = BUILDERS[buildername]
  api.chromium_android.configure_from_properties('base_config',
                                                 REPO_NAME='src',
                                                 REPO_URL=REPO_URL,
                                                 INTERNAL=False,
                                                 BUILD_CONFIG='Release')
  api.gclient.set_config('android_shared')
  api.gclient.apply_config('android')

  yield api.bot_update.ensure_checkout()
  api.path['checkout'] = api.path['slave_build'].join('src')

  yield api.chromium_android.download_build(bucket=builder['bucket'],
    path=builder['path'](api))

  # The directory extracted as src/full-build-linux and needs to be renamed to
  # src/out/Release
  # TODO(zty): remove the following once parent builder is zipping out/
  yield api.step(
      'rm out',
      ['rm', '-rf', api.path['checkout'].join('out')])
  yield api.step(
      'mkdir out',
      ['mkdir', '-p', api.path['checkout'].join('out')])
  yield api.step(
      'move build',
      ['mv', api.path['checkout'].join('full-build-linux'),
             api.path['checkout'].join('out','Release')])

  yield api.chromium_android.spawn_logcat_monitor()
  yield api.chromium_android.device_status_check()
  yield api.chromium_android.provision_devices()

  yield api.chromium_android.adb_install_apk(
      'ChromeShell.apk',
      'org.chromium.chrome.shell')

  tests_json_file = api.path['checkout'].join('out', 'perf-tests.json')
  yield api.chromium_android.list_perf_tests(browser='android-content-shell',
    json_output_file=tests_json_file)
  yield api.chromium_android.run_sharded_perf_tests(
      config=tests_json_file,
      perf_id=builder['perf_id'])

  yield api.chromium_android.logcat_dump()
  yield api.chromium_android.stack_tool_steps()
  yield api.chromium_android.test_report()

  yield api.chromium_android.cleanup_build()

def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)

def GenTests(api):
  for buildername in BUILDERS:
    yield (
        api.test('test_%s' % _sanitize_nonalpha(buildername)) +
        api.properties.generic(
            repo_name='src',
            repo_url=REPO_URL,
            buildername=buildername,
            parent_buildername='parent_buildername',
            parent_buildnumber='1729',
            parent_revision='deadbeef',
            revision='deadbeef',
            slavename='slavename',
            target='Release')
    )
