# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""ActiveMain definition."""


from config_bootstrap import Main


class SkiaAndroid(Main.Main3):
  project_name = 'SkiaAndroid'
  main_port = 8096
  subordinate_port = 8196
  main_port_alt = 8296
  repo_url = 'https://skia.googlesource.com/skia.git'
  buildbot_url = 'http://build.chromium.org/p/client.skia.android/'
  code_review_site = 'https://codereview.chromium.org'
