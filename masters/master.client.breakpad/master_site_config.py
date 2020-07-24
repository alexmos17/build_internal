# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMain definition."""

from config_bootstrap import Main

class Breakpad(Main.Main3):
  project_name = 'Breakpad'
  project_url = ('https://code.google.com/p/google-breakpad/wiki/'
                 'GettingStartedWithBreakpad')
  main_port = 8053
  subordinate_port = 8153
  main_port_alt = 8253
  buildbot_url = 'http://build.chromium.org/p/client.breakpad/'
