#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""A wrapper to start and stop xvfb.
"""

import optparse
import sys

# pylint: disable=W0403
import xvfb

from subordinate import build_directory

def main():
  parser = optparse.OptionParser(usage='%prog [options] subordinatename')

  parser.add_option('--build-dir', help='ignored')
  parser.add_option('--start', action='store_true', help='Start xvfb')
  parser.add_option('--stop', action='store_true', help='Stop xvfb')

  options, args = parser.parse_args()
  options.build_dir = build_directory.GetBuildOutputDirectory()

  if len(args) != 1:
    parser.error('Please specify the subordinate name')
  subordinate_name = args[0]

  if (not options.start) and (not options.stop):
    parser.error('Use one of --start OR --stop')

  if options.start:
    xvfb.StartVirtualX(subordinate_name, options.build_dir)

  if options.stop:
    xvfb.StopVirtualX(subordinate_name)

  return 0


if '__main__' == __name__:
  sys.exit(main())
