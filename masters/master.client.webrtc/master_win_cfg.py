# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import webrtc_factory

defaults = {}


def ConfigureBuilders(c, svn_url, branch, custom_deps_list=None):
  def win():
    return webrtc_factory.WebRTCFactory('src/out', 'win32', svn_url,
                                        branch, custom_deps_list)
  helper = master_config.Helper(defaults)
  B = helper.Builder
  F = helper.Factory
  S = helper.Scheduler

  scheduler = 'webrtc_win_scheduler'
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

  defaults['category'] = 'win'

  B('Win32 Debug', 'win32_debug_factory', scheduler=scheduler)
  F('win32_debug_factory', win().WebRTCFactory(
      target='Debug',
      options=ninja_options,
      tests=tests))

  B('Win32 Release', 'win32_release_factory', scheduler=scheduler)
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

  B('Win64 Debug', 'win64_debug_factory', scheduler=scheduler)
  F('win64_debug_factory', win().WebRTCFactory(
      target='Debug_x64',
      options=ninja_options,
      tests=tests,
      factory_properties={
          'gclient_env': {'GYP_DEFINES': 'target_arch=x64'},
      }))

  B('Win64 Release', 'win64_release_factory', scheduler=scheduler)
  F('win64_release_factory', win().WebRTCFactory(
      target='Release_x64',
      options=ninja_options,
      tests=tests,
      factory_properties={
          'gclient_env': {'GYP_DEFINES': 'target_arch=x64'},
      }))

  helper.Update(c)
