# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import webrtc_factory

defaults = {}


def win():
  return webrtc_factory.WebRTCFactory('src/out', 'win32')

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
S = helper.Scheduler

scheduler = 'webrtc_win_scheduler'
S(scheduler, branch='trunk', treeStableTimer=0)

tests = [
    'audio_decoder_unittests',
    'common_audio_unittests',
    'common_video_unittests',
    'libjingle_media_unittest',
    'libjingle_p2p_unittest',
    'libjingle_peerconnection_unittest',
    'libjingle_sound_unittest',
    'libjingle_unittest',
    'modules_tests',
    'modules_unittests',
    'neteq_unittests',
    'system_wrappers_unittests',
    'test_support_unittests',
    'tools_unittests',
    'video_engine_core_unittests',
    'video_engine_tests',
    'voice_engine_unittests',
]

baremetal_tests = [
    'audio_device_tests',
    'video_capture_tests',
    'vie_auto_test',
    'voe_auto_test',
    'webrtc_perf_tests',
]

ninja_options = ['--build-tool=ninja']

defaults['category'] = 'win'

B('Win32 Debug', 'win32_debug_factory', 'compile|testers|windows', scheduler,
  slavebuilddir='win')
F('win32_debug_factory', win().WebRTCFactory(
    target='Debug',
    options=ninja_options,
    tests=tests))

B('Win32 Release', 'win32_release_factory', 'compile|testers|windows',
  scheduler, slavebuilddir='win')
F('win32_release_factory', win().WebRTCFactory(
    target='Release',
    options=ninja_options,
    tests=tests,
    # No point having more than one bot complaining about missing sources.
    factory_properties={
        'gclient_env': {
            'GYP_GENERATOR_FLAGS': 'msvs_error_on_missing_sources=1',
        },
    }))

B('Win64 Debug', 'win64_debug_factory', 'compile|testers|windows', scheduler,
  slavebuilddir='win')
F('win64_debug_factory', win().WebRTCFactory(
    target='Debug_x64',
    options=ninja_options,
    tests=tests,
    factory_properties={
        'gclient_env': {'GYP_DEFINES': 'target_arch=x64'},
    }))

B('Win64 Release', 'win64_release_factory', 'compile|testers|windows',
  scheduler, slavebuilddir='win')
F('win64_release_factory', win().WebRTCFactory(
    target='Release_x64',
    options=ninja_options,
    tests=tests,
    factory_properties={
        'gclient_env': {'GYP_DEFINES': 'target_arch=x64'},
    }))

B('Win32 Release [large tests]', 'win32_largetests_factory',
  'compile|baremetal|windows', scheduler)
F('win32_largetests_factory', win().WebRTCFactory(
    target='Release',
    options=ninja_options,
    tests=baremetal_tests,
    factory_properties={
        'virtual_webcam': True,
        'show_perf_results': True,
        'expectations': True,
        'perf_id': 'webrtc-win-large-tests',
        'perf_config': {'a_default_rev': 'r_webrtc_rev'},
        'perf_measuring_tests': ['vie_auto_test',
                                 'webrtc_perf_tests'],
        'custom_cmd_line_tests': ['vie_auto_test',
                                  'voe_auto_test'],
    }))


def Update(c):
  helper.Update(c)
