# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMain definition."""

from config_bootstrap import Main

class NativeClientSDKMono(Main.NaClBase):
  project_name = 'NativeClientSDKMono'
  main_port = 8050
  subordinate_port = 8150
  main_port_alt = 8250
  buildbot_url = 'http://build.chromium.org/p/client.nacl.sdk.mono/'
