# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'bot_update',
  'chromium',
  'gclient',
  'gsutil',
  'path',
  'properties',
  'python',
  'step',
  'zip',
]

def GenSteps(api):
  api.chromium.cleanup_temp()
  api.gclient.set_config('v8')
  api.bot_update.ensure_checkout(force=True, no_shallow=True)
  if not api.path.exists(api.path['subordinate_build'].join('v8.svn')):
    api.gsutil.download_url(
        'gs://chromium-v8-auto-roll/bootstrap/v8.svn.zip',
        api.path['subordinate_build'],
        name='bootstrapping checkout')
    api.zip.unzip('unzipping',
                  api.path['subordinate_build'].join('v8.svn.zip'),
                  api.path['subordinate_build'].join('v8.svn'))
  api.step('svn update',
           ['svn', 'update'],
           cwd=api.path['subordinate_build'].join('v8.svn'))
  api.python(
      'increment version',
      api.path['checkout'].join(
          'tools', 'push-to-trunk', 'bump_up_version.py'),
      ['--author', 'v8-autoroll@chromium.org',
       '--svn', api.path['subordinate_build'].join('v8.svn'),
       '--svn-config', api.path['subordinate_build'].join('svn_config')],
      cwd=api.path['checkout'],
    )


def GenTests(api):
  yield api.test('standard') + api.properties.generic(mainname='client.v8')
