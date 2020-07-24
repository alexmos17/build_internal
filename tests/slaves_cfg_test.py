#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Ensure that all subordinates.cfg files are well formatted and without duplicity.
"""

import os
import sys

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_PATH, '..', 'scripts'))

from common import chromium_utils

sys.path.pop(0)

# List of subordinates that are allowed to be used more than once.
WHITELIST = ['build1-m6']

def main():
  status = 0
  subordinates = {}
  for subordinate in chromium_utils.GetAllSubordinates(fail_hard=True):
    mainname = subordinate['mainname']
    subordinatename = chromium_utils.EntryToSubordinateName(subordinate)
    if subordinate.get('subdir') == 'b':
      print 'Illegal subdir for %s: %s' % (mainname, subordinatename)
      status = 1
    if subordinatename and subordinate.get('hostname') not in WHITELIST:
      subordinates.setdefault(subordinatename, []).append(mainname)
  for subordinatename, mains in subordinates.iteritems():
    if len(mains) > 1:
      print '%s duplicated in mains: %s' % (subordinatename, ' '.join(mains))
      status = 1
  return status

if __name__ == '__main__':
  sys.exit(main())
