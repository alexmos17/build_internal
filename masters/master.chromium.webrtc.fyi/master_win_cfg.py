# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import chromium_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
S = helper.Scheduler
P = helper.Periodic


def win():
  return chromium_factory.ChromiumFactory('src/build', 'win32')

S('win_webrtc_scheduler', branch='trunk', treeStableTimer=0)
P('win_periodic_scheduler', periodicBuildTimer=4*60*60)

tests = [
    'webrtc_manual_browser_tests',
    'webrtc_manual_content_browsertests',
    'webrtc_content_unittests',
    'sizes',
]

defaults['category'] = 'win'

B('Win', 'win_webrtc_factory',
  scheduler='win_webrtc_scheduler|win_periodic_scheduler',
  notify_on_missing=True)
F('win_webrtc_factory', win().ChromiumWebRTCLatestFactory(
    slave_type='BuilderTester',
    target='Release',
    options=['--compiler=goma', '--', 'chromium_builder_webrtc'],
    tests=tests,
    compile_timeout=2400,
    factory_properties={
        'virtual_webcam': True,
        'show_perf_results': True,
        'perf_id': 'chromium-webrtc-trunk-tot-rel-win',
        'perf_config': {'a_default_rev': 'r_webrtc_rev'},
        'process_dumps': True,
        'start_crash_handler': True,
    }))


def Update(config, active_master, c):
  return helper.Update(c)
