# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.changes import svnpoller

from common import chromium_utils

from main import build_utils

def SyzygyFileSplitter(path):
  """split_file for Syzygy."""
  projects = ['trunk']
  return build_utils.SplitPath(projects, path)

def Update(config, active_main, c):
  syzygy_url = config.Main.syzygy_url
  syzygy_revlinktmpl = config.Main.googlecode_revlinktmpl % ('sawbuck', '%s')

  syzygy_poller = svnpoller.SVNPoller(svnurl=syzygy_url,
                                      svnbin=chromium_utils.SVN_BIN,
                                      split_file=SyzygyFileSplitter,
                                      pollinterval=30,
                                      revlinktmpl=syzygy_revlinktmpl)
  c['change_source'].append(syzygy_poller)
