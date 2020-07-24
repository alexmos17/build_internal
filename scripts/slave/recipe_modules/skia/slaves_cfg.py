# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


"""Utilities for working with subordinates.cfg files."""


import os


def _subordinates_cfg_path(main_name):
  return os.path.abspath(os.path.join(
      os.path.abspath(os.path.dirname(__file__)),
      os.pardir, os.pardir, os.pardir, os.pardir, 'mains',
      'main.' + main_name, 'subordinates.cfg'))


def get(main_name):
  """Return a dictionary of the buildsubordinates for the given main.

  Keys are subordinatenames and values are the unmodified subordinate dicts from the
  subordinates.cfg file for the given main.
  """
  vars = {}
  execfile(_subordinates_cfg_path(main_name), vars)
  subordinates_cfg = {}
  for subordinate_dict in vars['subordinates']:
    subordinates_cfg[subordinate_dict['hostname']] = subordinate_dict
  return subordinates_cfg

