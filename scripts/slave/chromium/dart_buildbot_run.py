#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Entry point for the dartium buildbots.

This script is called from buildbot and reports results using the buildbot
annotation scheme.
"""

import os
import sys

from common import chromium_utils

def main():
  builder_name = os.getenv('BUILDBOT_BUILDERNAME', default='')

  # Temporary until 1.6 ships on stable.
  if builder_name.endswith('-be') or builder_name.endswith("-dev"):
    script = 'src/dart/tools/dartium/buildbot_annotated_steps.py'
  else:
    script = 'src/dartium_tools/buildbot_annotated_steps.py'
  chromium_utils.RunCommand([sys.executable, script])

  # BIG HACK
  # Normal ninja clobbering does not work due to symlinks/python on windows
  # Full clobbering before building does not work since it will destroy
  # the ninja build files
  # So we basically clobber at the end here
  if chromium_utils.IsWindows() and 'full' in builder_name:
    chromium_utils.RemoveDirectory('src/out')
  return 0

if __name__ == '__main__':
  sys.exit(main())
