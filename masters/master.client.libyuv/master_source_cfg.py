# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from common import chromium_utils

from main import build_utils

from buildbot.changes import svnpoller


def TrunkOnlyFileSplitter(path):
  """Splits the SVN path into branch and filename sections."""

  # List of projects we are interested in. The project names must exactly
  # match paths in the Subversion repository, relative to the 'path' URL
  # argument. build_utils.SplitPath() will use them as branch names to
  # kick off the Schedulers for different projects.
  projects = ['trunk']
  return build_utils.SplitPath(projects, path)


def Update(config, c):
  poller = svnpoller.SVNPoller(
      svnurl=config.Main.libyuv_url,
      svnbin=chromium_utils.SVN_BIN,
      split_file=TrunkOnlyFileSplitter,
      pollinterval=30,
      histmax=10,
      revlinktmpl='http://code.google.com/p/libyuv/source/detail?r=%s')
  c['change_source'].append(poller)
