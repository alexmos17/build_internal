# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'base_android',
  'chromium',
  'gclient',
  'json',
  'path',
  'platform',
  'properties',
  'python',
  'step',
  'webrtc',
]


def GenSteps(api):
  config_vals = {}
  config_vals.update(
    dict((str(k),v) for k,v in api.properties.iteritems() if k.isupper())
  )
  api.webrtc.set_config('webrtc_android_apk_try_builder', **config_vals)

  # Replace src/third_party/webrtc with a WebRTC ToT checkout and force the
  # Chromium code to sync ToT.
  api.gclient.c.solutions[0].revision = 'HEAD'
  # TODO(kjellander): Switch to use the webrtc_revision gyp variable in DEPS
  # as soon we've switched over to use the trunk branch instead of the stable
  # branch (which is about to be retired).
  api.gclient.c.solutions[0].custom_deps['src/third_party/webrtc'] += (
      '@' + api.properties.get('revision'))

  api.step.auto_resolve_conflicts = True

  yield api.gclient.checkout()
  yield api.webrtc.apply_svn_patch()
  yield api.base_android.envsetup()
  yield api.base_android.runhooks()
  yield api.chromium.cleanup_temp()
  yield api.base_android.compile()

  for test in api.webrtc.NORMAL_TESTS:
    # The libjingle tests or video_engine_tests are not yet supported.
    if not test.startswith(('libjingle', 'video_engine_tests')):
      yield api.base_android.test_runner(test)


def GenTests(api):
  for build_config in ('Debug', 'Release'):
    for target_arch in ('intel', 'arm'):
      props = api.properties(
        TARGET_PLATFORM='android',
        TARGET_ARCH=target_arch,
        TARGET_BITS=32,
        BUILD_CONFIG=build_config,
        ANDROID_APK=True,
        revision='12345',
        patch_url='try_job_svn_patch'
      )
      yield (
        api.test('%s_%s' % (build_config, target_arch)) +
        props +
        api.platform('linux', 64) +
        api.step_data('envsetup',
            api.json.output({
                'FOO': 'bar',
                'GYP_DEFINES': 'my_new_gyp_def=aaa',
            }))
      )
