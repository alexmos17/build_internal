# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_bootstrap import Master

class ChromiumWebRTCFYI(Master.Master1):
  project_name = 'Chromium WebRTC FYI'
  master_port = 8056
  slave_port = 8156
  master_port_alt = 8256
  server_url = 'http://webrtc.googlecode.com'
  project_url = 'http://webrtc.googlecode.com'
  from_address = 'webrtc-cb-watchlist@google.com'
  permitted_domains = ('google.com', 'chromium.org', 'webrtc.org')
