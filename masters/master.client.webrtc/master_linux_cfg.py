# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import webrtc_factory

defaults = {}


def linux():
  return webrtc_factory.WebRTCFactory('src/out', 'linux2')

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
S = helper.Scheduler

scheduler = 'webrtc_linux_scheduler'
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
    'metrics_unittests',
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
    'audio_e2e_test',
    'audioproc_perf',
    'isac_fixed_perf',
    'libjingle_peerconnection_java_unittest',
    'video_capture_tests',
    'video_engine_tests',
    'vie_auto_test',
    'voe_auto_test',
]

ninja_options = ['--build-tool=ninja']

defaults['category'] = 'linux'

B('Linux32 Debug', 'linux32_debug_factory', scheduler=scheduler,
  auto_reboot=False)
F('linux32_debug_factory', linux().WebRTCFactory(
    target='Debug',
    options=ninja_options,
    tests=tests,
    factory_properties={
        'sharded_tests': tests,
        'force_isolated': True,
        'gclient_env': {'GYP_DEFINES': 'target_arch=ia32'},
    }))

B('Linux32 Release', 'linux32_release_factory', scheduler=scheduler,
  auto_reboot=False)
F('linux32_release_factory', linux().WebRTCFactory(
    target='Release',
    options=ninja_options,
    tests=tests,
    factory_properties={
        'sharded_tests': tests,
        'force_isolated': True,
        'gclient_env': {'GYP_DEFINES': 'target_arch=ia32'},
    }))

B('Linux64 Debug', 'linux64_debug_factory', scheduler=scheduler,
  auto_reboot=False)
F('linux64_debug_factory', linux().WebRTCFactory(
    target='Debug',
    options=ninja_options,
    tests=tests,
    factory_properties={
        'sharded_tests': tests,
        'force_isolated': True,
    }))

B('Linux64 Release', 'linux64_release_factory', scheduler=scheduler,
  auto_reboot=False)
F('linux64_release_factory', linux().WebRTCFactory(
    target='Release',
    options=ninja_options,
    tests=tests,
    factory_properties={
        'sharded_tests': tests,
        'force_isolated': True,
    }))

B('Linux Clang', 'linux_clang_factory', scheduler=scheduler,
  auto_reboot=False)
F('linux_clang_factory', linux().WebRTCFactory(
    target='Debug',
    options=ninja_options,
    tests=tests,
    factory_properties={
        'sharded_tests': tests,
        'force_isolated': True,
        'gclient_env': {'GYP_DEFINES': 'clang=1'},
    }))

B('Linux Memcheck', 'linux_memcheck_factory', scheduler=scheduler,
  auto_reboot=False)
F('linux_memcheck_factory', linux().WebRTCFactory(
    target='Release',
    options=ninja_options,
    tests=['memcheck_' + test for test in tests],
    factory_properties={
        'needs_valgrind': True,
        'gclient_env': {'GYP_DEFINES': 'build_for_tool=memcheck'},
    }))

B('Linux Tsan', 'linux_tsan_factory', scheduler=scheduler,
  auto_reboot=False)
F('linux_tsan_factory', linux().WebRTCFactory(
    target='Release',
    options=ninja_options,
    tests=['tsan_' + test for test in tests],
    factory_properties={
        'needs_valgrind': True,
        'gclient_env': {'GYP_DEFINES': 'build_for_tool=tsan'},
    }))

B('Linux Asan', 'linux_asan_factory', scheduler=scheduler,
  auto_reboot=False)
F('linux_asan_factory', linux().WebRTCFactory(
    target='Release',
    options=ninja_options,
    tests=tests,
    factory_properties={
        'asan': True,
        'sharded_tests': tests,
        'force_isolated': True,
        'gclient_env': {
            'GYP_DEFINES': ('asan=1 release_extra_cflags=-g '
                            'linux_use_tcmalloc=0 ')},
    }))

B('Linux64 Release [large tests]', 'linux_largetests_factory',
  scheduler=scheduler, auto_reboot=True)
F('linux_largetests_factory', linux().WebRTCFactory(
    target='Release',
    options=ninja_options,
    tests=baremetal_tests,
    factory_properties={
        'virtual_webcam': True,
        'show_perf_results': True,
        'expectations': True,
        'perf_id': 'webrtc-linux-large-tests',
        'perf_measuring_tests': ['audio_e2e_test',
                                 'audioproc_perf',
                                 'isac_fixed_perf',
                                 'vie_auto_test',
                                 'video_engine_tests'],
        'custom_cmd_line_tests': ['audio_e2e_test',
                                  'audioproc_perf',
                                  'isac_fixed_perf',
                                  'libjingle_peerconnection_java_unittest',
                                  'vie_auto_test',
                                  'voe_auto_test'],
    }))

# ChromeOS.
B('Chrome OS', 'chromeos_factory', scheduler=scheduler, auto_reboot=False)
F('chromeos_factory', linux().WebRTCFactory(
    target='Debug',
    options=ninja_options,
    tests=tests,
    factory_properties={
        'gclient_env': {'GYP_DEFINES': 'chromeos=1'},
    }))


def Update(c):
  helper.Update(c)
