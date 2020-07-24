# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from main import gatekeeper
from main import main_utils

# This is the list of the builder categories and the corresponding critical
# steps. If one critical step fails, gatekeeper will close the tree
# automatically.
# Note: don't include 'update scripts' since we can't do much about it when
# it's failing and the tree is still technically fine.
categories_steps = {
  '': ['update', 'runhooks', 'gn', 'compile'],
  'testers': [
    'Presubmit',
    'Static-Initializers',
    'Check',
    'Unittests',
    'OptimizeForSize',
    'Webkit',
    'Benchmarks',
    'Test262',
    'Mozilla',
    'GCMole',
   ],
}

exclusions = {
  'V8 Linux - mips - sim - builder': [],
  'V8 Linux - mips - sim': [],
  'V8 Linux - x87 - nosnap - debug': [],
}

forgiving_steps = ['update_scripts', 'update', 'svnkill', 'taskkill',
                   'gclient_revert']

def Update(config, active_main, c):
  c['status'].append(gatekeeper.GateKeeper(
      fromaddr=active_main.from_address,
      categories_steps=categories_steps,
      exclusions=exclusions,
      relayhost=config.Main.smtp,
      subject='buildbot %(result)s in %(projectName)s on %(builder)s, '
              'revision %(revision)s',
      extraRecipients=active_main.tree_closing_notification_recipients,
      lookup='google.com',
      forgiving_steps=forgiving_steps,
      tree_status_url=active_main.tree_status_url))
