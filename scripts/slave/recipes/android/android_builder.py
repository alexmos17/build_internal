# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'chromium_android',
  'bot_update',
  'gclient',
  'path',
  'properties',
  'tryserver',
]

BUILDERS = {
  'chromium.fyi': {
    'Android ARM64 Builder (dbg)': {
      'recipe_config': 'arm64_builder',
      'gclient_apply_config': ['android', 'chrome_internal'],
    },
    'Android x64 Builder (dbg)': {
      'recipe_config': 'x64_builder',
      'gclient_apply_config': ['android', 'chrome_internal'],
    },
    'Android MIPS Builder (dbg)': {
      'recipe_config': 'mipsel_builder',
      'gclient_apply_config': ['android', 'chrome_internal'],
    }
  },
  'tryserver.chromium': {
    'android_dbg_recipe': {
      'recipe_config': 'main_builder',
      'gclient_apply_config': ['android', 'chrome_internal'],
      'try': True,
      'upload': {
        'bucket': 'chromium-android',
        'path': lambda api: ('android_try_dbg_recipe/full-build-linux_%s.zip'
                             % api.properties['buildnumber']),
      },
    }
  },
  'chromium.perf.fyi': {
    'android_oilpan_builder': {
      'recipe_config': 'oilpan_builder',
      'gclient_apply_config': ['android', 'chrome_internal'],
      'kwargs': {
        'BUILD_CONFIG': 'Release',
      },
      'upload': {
        'bucket': 'chromium-android',
        'path': lambda api: (
          '%s/build_product_%s.zip' % (api.properties['buildername'],
                                       api.properties['got_revision'])),
      }
    },
  },
  'chromium.perf': {
    'Android Builder': {
      'recipe_config': 'perf',
      'gclient_apply_config': ['android', 'perf'],
      'kwargs': {
        'BUILD_CONFIG': 'Release',
      },
      'upload': {
        'bucket': 'chrome-perf',
        'path': lambda api: ('android_perf_rel/full-build-linux_%s.zip'
                             % api.properties['got_revision']),
      }
    }
  }
}

def GenSteps(api):
  mastername = api.properties['mastername']
  buildername = api.properties['buildername']
  bot_config = BUILDERS[mastername][buildername]
  droid = api.chromium_android

  default_kwargs = {
    'REPO_URL': 'svn://svn-mirror.golo.chromium.org/chrome/trunk/src',
    'INTERNAL': False,
    'REPO_NAME': 'src',
    'BUILD_CONFIG': 'Debug'
  }
  default_kwargs.update(bot_config.get('kwargs', {}))
  droid.configure_from_properties(bot_config['recipe_config'], **default_kwargs)
  droid.c.set_val({'deps_file': 'DEPS'})

  api.gclient.set_config('chromium')
  for c in bot_config.get('gclient_apply_config', []):
    api.gclient.apply_config(c)

  yield api.bot_update.ensure_checkout()
  yield droid.clean_local_files()
  yield droid.runhooks()

  if bot_config.get('try', False):
    yield api.tryserver.maybe_apply_issue()

  yield droid.compile()
  yield droid.check_webview_licenses()
  yield droid.findbugs()

  upload_config = bot_config.get('upload')
  if upload_config:
    yield droid.upload_build(upload_config['bucket'],
                             upload_config['path'](api))
  yield droid.cleanup_build()


def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)

def GenTests(api):
  # tests bots in BUILDERS
  for mastername, builders in BUILDERS.iteritems():
    for buildername in builders:
      yield (
        api.test('full_%s_%s' % (_sanitize_nonalpha(mastername),
                                 _sanitize_nonalpha(buildername))) +
        api.properties.generic(buildername=buildername,
            repository='svn://svn.chromium.org/chrome/trunk/src',
            buildnumber=257,
            mastername=mastername,
            issue='8675309',
            patchset='1',
            revision='267739',
            got_revision='267739'))
