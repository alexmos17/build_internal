# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'gclient',
  'path',
]

def GenSteps(api):
  api.gclient.use_mirror = True

  src_cfg = api.gclient.make_config()
  soln = src_cfg.solutions.add()
  soln.name = 'src'
  soln.url = 'svn://svn.chromium.org/chrome/trunk/src'
  api.gclient.c = src_cfg
  api.gclient.checkout()

  api.gclient.spec_alias = 'WebKit'
  bl_cfg = api.gclient.make_config()
  soln = bl_cfg.solutions.add()
  soln.name = 'WebKit'
  soln.url = 'svn://svn.chromium.org/blink/trunk'
  bl_cfg.got_revision_mapping['src/blatley'] = 'got_blatley_revision'
  api.gclient.checkout(
      gclient_config=bl_cfg,
      cwd=api.path['slave_build'].join('src', 'third_party'))

  api.gclient.break_locks()
  del api.gclient.spec_alias

def GenTests(api):
  yield api.test('basic')
