# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_public import Master3

class Syzygy(Master3):
  project_name = 'Syzygy'
  project_url = 'http://sawbuck.googlecode.com'
  master_port = 8042
  slave_port = 8142
  master_port_alt = 8242
