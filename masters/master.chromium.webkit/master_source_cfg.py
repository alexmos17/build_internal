# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.changes import svnpoller
from buildbot.scheduler import AnyBranchScheduler

from common import chromium_utils

from main import build_utils
from main import gitiles_poller
from main import svn_poller_with_comparator

def WebkitFileSplitter(path):
  """split_file for webkit.org repository."""
  projects = ['trunk']
  return build_utils.SplitPath(projects, path)

def Update(config, _active_main, c):
  # Polls config.Main.trunk_url for changes
  cr_poller = gitiles_poller.GitilesPoller(
      'https://chromium.googlesource.com/chromium/src',
      pollInterval=30, project='chromium')
  c['change_source'].append(cr_poller)

  webkit_url = 'http://src.chromium.org/viewvc/blink?view=rev&revision=%s'
  webkit_poller = svnpoller.SVNPoller(
      svnurl = config.Main.webkit_root_url,
      svnbin=chromium_utils.SVN_BIN,
      split_file=WebkitFileSplitter,
      pollinterval=30,
      revlinktmpl=webkit_url,
      cachepath='webkit.svnrev',
      project='webkit')
  c['change_source'].append(webkit_poller)

  c['schedulers'].append(AnyBranchScheduler(
      name='global_scheduler', branches=['trunk', 'main'], treeStableTimer=60,
      builderNames=[]))

  c['schedulers'].append(AnyBranchScheduler(
      name='global_deps_scheduler', branches=['main'], treeStableTimer=60,
      builderNames=[]))
