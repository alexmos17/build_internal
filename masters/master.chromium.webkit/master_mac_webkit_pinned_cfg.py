# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# WebKit test builders using the Skia graphics library.

from master import master_config
from master.factory import chromium_factory

import config

ActiveMaster = config.Master.ChromiumWebkit

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
D = helper.Dependent
F = helper.Factory
S = helper.Scheduler

def mac(): return chromium_factory.ChromiumFactory('src/xcodebuild', 'darwin')
def mac_out(): return chromium_factory.ChromiumFactory('src/out', 'darwin')

defaults['category'] = '2webkit mac deps'

################################################################################
## Release
################################################################################

# Archive location
rel_builddir = 'webkit-mac-pinned-rel'
rel_archive = master_config.GetArchiveUrl('ChromiumWebkit',
    'WebKit Mac Builder (deps)',
    rel_builddir, 'mac')

#
# Main release scheduler for chromium
#
rel_scheduler = 's2_chromium_rel'
S(rel_scheduler, branch='src', treeStableTimer=60)

#
# Dependent scheduler for the dbg builder
#
rel_dep_scheduler = 's2_chromium_rel_dep'
D(rel_dep_scheduler, rel_scheduler)

#
# Mac Rel Builder
#
B('WebKit Mac Builder (deps)', 'f_webkit_mac_rel', auto_reboot=False,
  scheduler=rel_scheduler, builddir=rel_builddir)
F('f_webkit_mac_rel', mac_out().ChromiumFactory(
    slave_type='Builder',
    options=['--build-tool=ninja', '--compiler=goma-clang', '--',
        'test_shell', 'test_shell_tests', 'webkit_unit_tests',
        'DumpRenderTree'],
    factory_properties={
        'gclient_env': {
            'GYP_GENERATORS':'ninja',
        },
        'layout_test_platform': 'chromium-mac',
    }))

#
# Mac Rel WebKit testers
#
B('WebKit Mac10.6 (deps)', 'f_webkit_rel_tests', scheduler=rel_dep_scheduler)
F('f_webkit_rel_tests', mac().ChromiumFactory(
    slave_type='Tester',
    build_url=rel_archive,
    tests=[
      'test_shell',
      'webkit',
      'webkit_lint',
      'webkit_unit',
    ],
    factory_properties={
      'additional_expectations': [
        ['webkit', 'tools', 'layout_tests', 'test_expectations.txt' ],
      ],
      'archive_webkit_results': ActiveMaster.is_production_host,
      'generate_gtest_json': True,
      'layout_test_platform': 'chromium-mac',
      'test_results_server': 'test-results.appspot.com',
    }))

################################################################################
##
################################################################################

def Update(_config, active_master, c):
  return helper.Update(c)
