# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMain definition for main.client.polymer."""

from config_bootstrap import Main

class Polymer(Main.Main3):
  project_name = 'Polymer'
  project_url = 'http://github.com/Polymer/'
  main_port = 8044
  subordinate_port = 8144
  main_port_alt = 8244
  buildbot_url = 'http://build.chromium.org/p/client.polymer/'
