# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import chromium_notifier
from master import master_utils

# This is the list of the builder categories and the corresponding critical
# steps. If one critical step fails, the blame list will be notified.
# Note: don't include 'update scripts' since we can't do much about it when
# it's failing and the tree is still technically fine.
categories_steps = {
  '': [
    'update',
    'runhooks',
    'compile',
    'Presubmit',
    'Static-Initializers',
    'Check',
    'OptimizeForSize',
    'Mjsunit',
    'Webkit',
    'Test262',
    'Mozilla',
    'GCMole',
    'Fuzz',
    'Deopt Fuzz',
    'webkit_tests',
    'interactive_ui_tests',
    'heapcheck test: base_unittests',
    'heapcheck test: unit',
    'heapcheck test: net',
  ],
}

exclusions = {
  'V8 Linux - full debug': ['Mozilla'],
  'V8 Linux - nosnap - full debug ': ['Mozilla'],
  'V8 Win32 - full debug ': ['Mozilla'],
  'V8 Mac - full debug': ['Mozilla'],
  'V8 Linux - mips - sim': ['compile'],
  'V8 Linux - recipe': [],
  'NaCl V8 Linux': ['Check'],
  'NaCl V8 Linux64 - stable': ['Check'],
  'NaCl V8 Linux64 - canary': ['Check'],
  'Webkit - dbg': ['webkit_tests'],
  'Webkit Mac - dbg': ['webkit_tests'],
}

forgiving_steps = ['update_scripts', 'update', 'svnkill', 'taskkill',
                   'gclient_revert']

def Update(config, active_master, c):
  c['status'].append(chromium_notifier.ChromiumNotifier(
      fromaddr=active_master.from_address,
      categories_steps=categories_steps,
      exclusions=exclusions,
      relayhost=config.Master.smtp,
      sendToInterestedUsers=True,
      status_header='buildbot failure in %(project)s on %(builder)s, %(steps)s',
      lookup=master_utils.FilterDomain(),
      forgiving_steps=forgiving_steps))
