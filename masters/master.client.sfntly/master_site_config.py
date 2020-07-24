# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMain definition."""

from config_bootstrap import Main

class Sfntly(Main.Main3):
  project_name = 'Sfntly'
  project_url = 'http://code.google.com/p/sfntly/'
  main_port = 8048
  subordinate_port = 8148
  main_port_alt = 8248
  buildbot_url = 'http://build.chromium.org/p/client.sfntly/'
