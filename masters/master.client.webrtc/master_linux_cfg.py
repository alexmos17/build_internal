# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import chromium_factory
from master.factory import webrtc_factory

defaults = {}


def ConfigureBuilders(c, svn_url, branch, custom_deps_list=None):
  def linux():
    return webrtc_factory.WebRTCFactory('src/out', 'linux2', svn_url,
                                        branch, custom_deps_list)
  def android():
    return webrtc_factory.WebRTCFactory('', 'linux2', svn_url,
                                        branch, nohooks_on_update=True,
                                        target_os='android')

  helper = master_config.Helper(defaults)
  B = helper.Builder
  F = helper.Factory
  S = helper.Scheduler

  scheduler = 'webrtc_linux_scheduler'
  S(scheduler, branch=branch, treeStableTimer=0)

  tests = [
      'audio_decoder_unittests',
      'common_audio_unittests',
      'common_video_unittests',
      'metrics_unittests',
      'modules_integrationtests',
      'modules_unittests',
      'neteq_unittests',
      'system_wrappers_unittests',
      'test_support_unittests',
      'tools_unittests',
      'video_engine_core_unittests',
      'voice_engine_unittests',
  ]

  ninja_options = ['--build-tool=ninja']

  defaults['category'] = 'linux'

  B('Linux32 Debug', 'linux32_debug_factory', scheduler=scheduler)
  F('linux32_debug_factory', linux().WebRTCFactory(
      target='Debug',
      options=ninja_options,
      tests=tests,
      factory_properties={'gclient_env': {'GYP_DEFINES': 'target_arch=ia32'}}))
  B('Linux32 Release', 'linux32_release_factory', scheduler=scheduler)
  F('linux32_release_factory', linux().WebRTCFactory(
      target='Release',
      options=ninja_options,
      tests=tests,
      factory_properties={'gclient_env': {'GYP_DEFINES': 'target_arch=ia32'}}))

  B('Linux64 Debug', 'linux64_debug_factory', scheduler=scheduler)
  F('linux64_debug_factory', linux().WebRTCFactory(
      target='Debug',
      options=ninja_options,
      tests=tests))
  B('Linux64 Release', 'linux64_release_factory', scheduler=scheduler)
  F('linux64_release_factory', linux().WebRTCFactory(
      target='Release',
      options=ninja_options,
      tests=tests))

  B('Linux Clang', 'linux_clang_factory', scheduler=scheduler)
  F('linux_clang_factory', linux().WebRTCFactory(
      target='Debug',
      options=ninja_options,
      tests=tests,
      factory_properties={'gclient_env': {'GYP_DEFINES': 'clang=1'}}))

  B('Linux Memcheck', 'linux_memcheck_factory', scheduler=scheduler)
  F('linux_memcheck_factory', linux().WebRTCFactory(
      target='Release',
      options=ninja_options,
      tests=tests,
      factory_properties={'needs_valgrind': True,
                          'gclient_env':
                          {'GYP_DEFINES': 'build_for_tool=memcheck'}}))
  B('Linux Tsan', 'linux_tsan_factory', scheduler=scheduler)
  F('linux_tsan_factory', linux().WebRTCFactory(
      target='Release',
      options=ninja_options,
      tests=tests,
      factory_properties={'needs_valgrind': True,
                          'gclient_env':
                          {'GYP_DEFINES': 'build_for_tool=tsan'}}))
  B('Linux Asan', 'linux_asan_factory', scheduler=scheduler)
  F('linux_asan_factory', linux().WebRTCFactory(
      target='Release',
      options=ninja_options,
      tests=tests,
      factory_properties={'asan': True,
                          'gclient_env':
                          {'GYP_DEFINES': ('asan=1 release_extra_cflags=-g '
                                           ' linux_use_tcmalloc=0 ')}}))

  # Android.
  B('Android NDK', 'android_ndk_factory', scheduler=scheduler)
  F('android_ndk_factory', android().ChromiumAnnotationFactory(
    target='Debug',
    slave_type='AnnotatedBuilderTester',
    annotation_script='src/build/android/buildbot/bb_run_bot.py',
    factory_properties={
        'android_bot_id': 'webrtc-builder-dbg',
    }))

  # ChromeOS.
  B('Chrome OS', 'chromeos_factory', scheduler=scheduler)
  F('chromeos_factory', linux().WebRTCFactory(
      target='Debug',
      options=ninja_options,
      tests=tests,
      factory_properties={'gclient_env': {'GYP_DEFINES': 'chromeos=1'}}))

  helper.Update(c)
