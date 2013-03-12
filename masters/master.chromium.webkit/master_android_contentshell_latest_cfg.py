# Copyright (c) 2013 The Chromium Authors. All rights reserved.
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
S = helper.Scheduler

def linux_android(): return chromium_factory.ChromiumFactory('',
    'linux2', nohooks_on_update=True, target_os='android', full_checkout=True)


################################################################################
## Release
################################################################################

defaults['category'] = '9content shell'

#
# Main release scheduler for WebKit
#
S('s4_contentshell_webkit_rel', branch='trunk', treeStableTimer=60)

#
# Content Shell Layouttests
#
B('WebKit (Content Shell) Android', 'f_contentshell_android_rel',
  scheduler='s4_contentshell_webkit_rel')

F('f_contentshell_android_rel',
  linux_android().ChromiumWebkitLatestAnnotationFactory(
    annotation_script='src/build/android/buildbot/bb_run_bot.py',
    factory_properties={
        'additional_drt_flag': '--dump-render-tree',
        'additional_expectations_files': [
            [ 'third_party',
              'WebKit',
              'LayoutTests',
              'platform',
              'chromium',
              'ContentShellTestExpectations' ],
        ],
        'android_bot_id': 'webkit-latest-contentshell-rel',
        'archive_webkit_results': ActiveMaster.is_production_host,
        'driver_name': 'content_shell',
        'generate_gtest_json': True,
        'test_results_server': 'test-results.appspot.com',
        }))

def Update(_config, active_master, c):
  return helper.Update(c)
