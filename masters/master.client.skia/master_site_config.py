# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMain definition."""


from config_bootstrap import Main


class Skia(Main.Main3):
  project_name = 'Skia'
  main_port = 8084
  subordinate_port = 8184
  main_port_alt = 8284
  repo_url = 'https://skia.googlesource.com/skia.git'
  buildbot_url = 'http://build.chromium.org/p/client.skia/'
  code_review_site = 'https://codereview.chromium.org'
