# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'bot_update',
  'chromium',
  'gclient',
  'path',
  'platform',
  'properties',
  'step',
  'step_history',
  'tryserver',
]


BUILDERS = {
  'chromium.linux': {
    'builders': {
      'Android GN': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
        },
        'gclient_apply_config': ['android'],
      },
      'Android GN (dbg)': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
        },
        'gclient_apply_config': ['android'],
      },
      'Linux GN': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
      },
      'Linux GN (dbg)': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
        },
      },
    },
  },
  'tryserver.chromium': {
    'builders': {
      'android_chromium_gn_compile_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
        },
        'gclient_apply_config': ['android'],
      },
      'android_chromium_gn_compile_dbg': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
        },
        'gclient_apply_config': ['android'],
      },
      'linux_chromium_gn_rel': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
      },
      'linux_chromium_gn_dbg': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
        },
      },
    },
  },
  'fake_tryserver': {
    'builders': {
      'unittest_fake_trybotname': {
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
        },
      },
    },
  },
}

def GenSteps(api):
  # TODO: crbug.com/358481 . The build_config should probably be a property
  # passed in from slaves.cfg, but that doesn't exist today, so we need a
  # lookup mechanism to map bot name to build_config.
  mastername = api.properties.get('mastername')
  buildername = api.properties.get('buildername')
  master_dict = BUILDERS.get(mastername, {})
  bot_config = master_dict.get('builders', {}).get(buildername)
  is_tryserver = api.tryserver.is_tryserver
  if is_tryserver:
    api.step.auto_resolve_conflicts = True

  api.chromium.set_config('chromium',
                          **bot_config.get('chromium_config_kwargs', {}))

  # Note that we have to call gclient.set_config() and apply_config() *after*
  # calling chromium.set_config(), above, because otherwise the chromium
  # call would reset the gclient config to its defaults.
  api.gclient.set_config('chromium')
  for c in bot_config.get('gclient_apply_config', []):
    api.gclient.apply_config(c)

  # TODO(dpranke): crbug.com/358435. We need to figure out how to separate
  # out the retry and recovery logic from the rest of the recipe.

  yield api.bot_update.ensure_checkout()
  if not api.step_history.last_step().json.output['did_run']:
    yield api.gclient.checkout(revert=True,
                               abort_on_failure=(not is_tryserver),
                               can_fail_build=(not is_tryserver))

    if is_tryserver:
      if any(step.retcode != 0 for step in api.step_history.values()):
        yield api.path.rmcontents('slave build directory',
                                  api.path['slave_build'])
        yield api.gclient.checkout(revert=False,
                                   abort_on_failure=True,
                                   can_fail_build=True)
      yield api.tryserver.maybe_apply_issue()

  yield api.chromium.runhooks(run_gyp=False)

  yield api.chromium.run_gn()

  yield api.chromium.compile(targets=['all'])

  # TODO(dpranke): crbug.com/353854. Run gn_unittests and other tests
  # when they are also being run as part of the try jobs.


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)


def GenTests(api):
  # api.gclient.checkout() actually contains a revert call and a sync call,
  # so we test that either of them failing is handled correctly.
  yield (
      api.test('unittest_sync_fails') +
      api.properties.tryserver(buildername='unittest_fake_trybotname',
                               mastername='fake_tryserver') +
      api.platform.name('linux') +
      api.step_data('gclient sync', retcode=1)
  )

  yield (
      api.test('unittest_revert_fails') +
      api.properties.tryserver(buildername='unittest_fake_trybotname',
                               mastername='fake_tryserver') +
      api.platform.name('linux') +
      api.step_data('gclient revert', retcode=1)
  )

  # Here both checkout/syncs fail, so we should abort before every trying
  # to apply the patch.
  yield (
      api.test('unittest_second_sync_fails') +
      api.properties.tryserver(buildername='unittest_fake_trybotname',
                               mastername='fake_tryserver') +
      api.platform.name('linux') +
      api.step_data('gclient sync', retcode=1) +
      api.step_data('gclient sync (2)', retcode=1)
  )

  # TODO: crbug.com/354674. Figure out where to put "simulation"
  # tests. We should have one test for each bot this recipe runs on.

  # TODO(machenbach): Prefix test names with try server name like in other bot
  # specific tests. Get bot names from BUILDERS dict.
  trybot_names = [
    'android_chromium_gn_compile_dbg',
    'android_chromium_gn_compile_rel',
    'linux_chromium_gn_dbg',
    'linux_chromium_gn_rel',
  ]
  for buildername in trybot_names:
    yield (
        api.test('full_%s' % buildername) +
        api.properties.tryserver(buildername=buildername,
                                 mastername='tryserver.chromium') +
        api.platform.name('linux')
    )

  buildbot_names = [
    'Android GN',
    'Android GN (dbg)',
    'Linux GN',
    'Linux GN (dbg)',
  ]
  for buildername in buildbot_names:
    yield (
        api.test('full_chromium_linux_%s' % _sanitize_nonalpha(buildername)) +
        api.properties.generic(buildername=buildername,
                               mastername='chromium.linux') +
        api.platform.name('linux')
    )
