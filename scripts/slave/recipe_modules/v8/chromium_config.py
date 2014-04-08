# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave.recipe_config import BadConf
from slave.recipe_config_types import Path
from slave import recipe_config
from RECIPE_MODULES.chromium import CONFIG_CTX


@CONFIG_CTX()
def v8(c):
  targ_arch = c.gyp_env.GYP_DEFINES.get('target_arch')
  if not targ_arch:  # pragma: no cover
    raise recipe_config.BadConf('v8 must have a valid target_arch.')
  c.gyp_env.GYP_DEFINES['v8_target_arch'] = targ_arch
  del c.gyp_env.GYP_DEFINES['component']
  c.build_dir = Path('[CHECKOUT]', 'out')
  c.compile_py.build_tool = 'make'

  if c.HOST_PLATFORM == 'mac':
    c.compile_py.build_tool = 'xcode'
  elif c.HOST_PLATFORM == 'win':
    c.compile_py.build_tool = 'vs'
    c.build_dir = Path('[CHECKOUT]', 'build')

  if c.BUILD_CONFIG == 'Debug':
    c.gyp_env.GYP_DEFINES['v8_optimized_debug'] = 1


@CONFIG_CTX(includes=['v8'])
def no_lsan(c):
  c.gyp_env.GYP_DEFINES['lsan'] = 0


@CONFIG_CTX(includes=['v8'])
def no_snapshot(c):
  c.gyp_env.GYP_DEFINES['v8_use_snapshot'] = 'false'


@CONFIG_CTX(includes=['v8'])
def novfp3(c):
  c.gyp_env.GYP_DEFINES['v8_can_use_vfp3_instructions'] = 'false'


@CONFIG_CTX(includes=['v8'])
def no_optimized_debug(c):
  if c.BUILD_CONFIG == 'Debug':
    c.gyp_env.GYP_DEFINES['v8_optimized_debug'] = 0


@CONFIG_CTX(includes=['v8'])
def optimized_debug(c):
  if c.BUILD_CONFIG == 'Debug':
    c.gyp_env.GYP_DEFINES['v8_optimized_debug'] = 2


@CONFIG_CTX(includes=['v8'])
def verify_heap(c):
  c.gyp_env.GYP_DEFINES['v8_enable_verify_heap'] = 1
