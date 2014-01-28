# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_public import Master1

class ChromiumEndure(Master1):
  project_name = 'Chromium Endure'
  master_port = 8026
  slave_port = 8126
  master_port_alt = 8226
