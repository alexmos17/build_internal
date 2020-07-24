# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from main import main_config
from main.factory import chromium_factory

import main_site_config

ActiveMain = main_site_config.ChromiumWebkit

defaults = {}

helper = main_config.Helper(defaults)
B = helper.Builder
T = helper.Triggerable
F = helper.Factory

def win():
  return chromium_factory.ChromiumFactory('src/build', 'win32')

defaults['category'] = 'deps'

################################################################################
## Release
################################################################################

# Archive location
rel_archive = main_config.GetGSUtilUrl('chromium-build-transfer',
                                         'WebKit Win Builder (deps)')

#
# Trigger scheduler for the dbg builder
#
T('s1_chromium_rel_trigger')

#
# Win Rel Builder
#
B('WebKit Win Builder (deps)', 'f_webkit_win_rel',
  scheduler='global_deps_scheduler', builddir='webkit-win-pinned-rel',
  auto_reboot=False)
F('f_webkit_win_rel', win().ChromiumFactory(
    subordinate_type='Builder',
    build_url=rel_archive,
    project='all.sln;blink_tests',
    factory_properties={
        'trigger': 's1_chromium_rel_trigger',
        'gclient_env': {
        },
    }))

#
# Win Rel WebKit testers
#
B('WebKit XP (deps)', 'f_webkit_rel_tests', scheduler='s1_chromium_rel_trigger')
F('f_webkit_rel_tests', win().ChromiumFactory(
    subordinate_type='Tester',
    build_url=rel_archive,
    tests=chromium_factory.blink_tests,
    factory_properties={
      'additional_expectations': [
        ['content', 'test', 'test_expectations.txt' ],
      ],
      'archive_webkit_results': ActiveMain.is_production_host,
      'generate_gtest_json': True,
      'test_results_server': 'test-results.appspot.com',
    }))

def Update(_config, _active_main, c):
  return helper.Update(c)
