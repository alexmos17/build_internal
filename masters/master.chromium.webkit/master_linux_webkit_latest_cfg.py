# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import chromium_factory

import config

ActiveMaster = config.Master.ChromiumWebkit

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory

def linux():
  return chromium_factory.ChromiumFactory('src/out', 'linux2')


################################################################################
## Release
################################################################################

defaults['category'] = 'layout'

#
# Linux Rel Builder/Tester
#
B('WebKit Linux', 'f_webkit_linux_rel', scheduler='global_scheduler')
F('f_webkit_linux_rel', linux().ChromiumFactory(
    tests=[
        'webkit',
        'webkit_lint',
        'webkit_unit',
    ],
    options=[
        '--build-tool=ninja',
        '--compiler=goma',
        '--',
        'content_shell',
        'DumpRenderTree',
        'test_shell',
        'webkit_unit_tests',
    ],
    factory_properties={
        'archive_webkit_results': ActiveMaster.is_production_host,
        'gclient_env': { 'GYP_GENERATORS': 'ninja' },
        'generate_gtest_json': True,
        'test_results_server': 'test-results.appspot.com',
        'blink_config': 'blink',
    }))

B('WebKit Linux 32', 'f_webkit_linux_rel', scheduler='global_scheduler')

asan_gyp = ('asan=1 linux_use_tcmalloc=0 '
            'release_extra_cflags="-g -O1 -fno-inline-functions -fno-inline"')

B('WebKit Linux ASAN', 'f_webkit_linux_rel_asan', scheduler='global_scheduler',
  auto_reboot=False)
F('f_webkit_linux_rel_asan', linux().ChromiumFactory(
    tests=['webkit'],
    options=[
        '--build-tool=ninja',
        '--compiler=goma-clang',
        '--',
        'content_shell',
        'DumpRenderTree'
    ],
    factory_properties={
        'additional_expectations': [
            ['webkit', 'tools', 'layout_tests', 'test_expectations_asan.txt' ],
        ],
        'gs_bucket': 'gs://webkit-asan',
        'gclient_env': {'GYP_DEFINES': asan_gyp, 'GYP_GENERATORS': 'ninja'},
        'time_out_ms': '18000',
        'blink_config': 'blink',
    }))


################################################################################
## Debug
################################################################################

#
# Linux Dbg Webkit builders/testers
#

B('WebKit Linux (dbg)', 'f_webkit_dbg_tests', scheduler='global_scheduler',
  auto_reboot=False)
F('f_webkit_dbg_tests', linux().ChromiumFactory(
    target='Debug',
    tests=[
        'webkit',
        'webkit_lint',
        'webkit_unit',
    ],
    options=[
        '--build-tool=ninja',
        '--compiler=goma',
        '--',
        'content_shell',
        'DumpRenderTree',
        'test_shell',
        'webkit_unit_tests',
    ],
    factory_properties={
        'archive_webkit_results': ActiveMaster.is_production_host,
        'generate_gtest_json': True,
        'test_results_server': 'test-results.appspot.com',
        'gclient_env': { 'GYP_GENERATORS': 'ninja' },
        'blink_config': 'blink',
    }))

def Update(_config, _active_master, c):
  return helper.Update(c)
