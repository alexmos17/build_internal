# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMaster definition."""

from config_public import Master3

class WebRTC(Master3):
  project_name = 'WebRTC'
  master_port = 8060
  slave_port = 8160
  master_port_alt = 8260
  server_url = 'http://webrtc.googlecode.com'
  project_url = 'http://webrtc.googlecode.com'
  from_address = 'webrtc-cb-watchlist@google.com'
  master_domain = 'webrtc.org'
  permitted_domains = ('google.com', 'chromium.org', 'webrtc.org')
  base_app_url = 'https://webrtc-status.appspot.com'
  tree_status_url = base_app_url + '/status'
  store_revisions_url = base_app_url + '/revisions'
  last_good_url = base_app_url + '/lkgr'
