# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMain definition."""

from config_bootstrap import Main

class PushCanary(Main.Base):
  project_name = 'Chromium PushCanary'
  main_host = 'localhost'
  main_port = 8081
  subordinate_port = 8181
  main_port_alt = 8281
  buildbot_url = 'http://localhost:8080/'
