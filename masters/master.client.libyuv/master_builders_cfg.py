# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master import master_config
from master.factory import libyuv_factory

defaults = {}

helper = master_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
S = helper.Scheduler

def linux(): return libyuv_factory.LibyuvFactory('src/out', 'linux2')
def mac(): return libyuv_factory.LibyuvFactory('src/out', 'darwin')
def mac_ios(): return libyuv_factory.LibyuvFactory('src/out', 'darwin',
                                                   target_os='ios')
def win(): return libyuv_factory.LibyuvFactory('src/out', 'win32')
def android():
  return libyuv_factory.LibyuvFactory('', 'linux2', nohooks_on_update=True,
                                      target_os='android')

scheduler_name = 'libyuv_scheduler'
S(scheduler_name, branch='trunk', treeStableTimer=60)

test_targets = ['libyuv_unittest']
ninja_options = ['--build-tool=ninja']
win_msvs_missing_files_factory_properties = {
    'gclient_env': {'GYP_GENERATOR_FLAGS': 'msvs_error_on_missing_sources=1'}}
win_msvs_2012_factory_properties = {
    'gclient_env': {
        'GYP_GENERATORS': 'ninja',
        'GYP_MSVS_VERSION': '2012',
    },
}
win_msvs_2012_x64_factory_properties = {
    'gclient_env': {
        'GYP_DEFINES': 'target_arch=x64',
        'GYP_GENERATORS': 'ninja',
        'GYP_MSVS_VERSION': '2012',
    },
}

mac_ios_factory_properties = {
    'gclient_env': {
        'GYP_CROSSCOMPILE': '1',
        'GYP_DEFINES': 'OS=ios target_arch=armv7',
    }
}

asan_gclient_env = {
    'GYP_DEFINES': ('asan=1 release_extra_cflags=-g linux_use_tcmalloc=0 ')}

# Windows.
defaults['category'] = 'win'

B('Win32 Debug', 'win32_debug_factory', scheduler=scheduler_name)
F('win32_debug_factory', win().LibyuvFactory(
    target='Debug',
    options=ninja_options,
    tests=test_targets,
    factory_properties=win_msvs_missing_files_factory_properties))

B('Win32 Release', 'win32_release_factory', scheduler=scheduler_name)
F('win32_release_factory', win().LibyuvFactory(
    target='Release',
    options=ninja_options,
    tests=test_targets,
    factory_properties=win_msvs_missing_files_factory_properties))

B('Win64 Debug', 'win64_debug_factory', scheduler=scheduler_name)
F('win64_debug_factory', win().LibyuvFactory(
    target='Debug_x64',
    options=ninja_options,
    tests=test_targets,
    factory_properties={
        'gclient_env': {'GYP_DEFINES': 'target_arch=x64'},
    }))

B('Win64 Release', 'win64_release_factory', scheduler=scheduler_name)
F('win64_release_factory', win().LibyuvFactory(
    target='Release_x64',
    options=ninja_options,
    tests=test_targets,
    factory_properties={
        'gclient_env': {'GYP_DEFINES': 'target_arch=x64'},
    }))

B('Win32 Debug (VS2012)', 'win32_2012_debug_factory', scheduler=scheduler_name)
F('win32_2012_debug_factory', win().LibyuvFactory(
    target='Debug',
    options=ninja_options,
    tests=test_targets,
    factory_properties=win_msvs_2012_factory_properties))

B('Win32 Release (VS2012)', 'win32_2012_release_factory',
  scheduler=scheduler_name)
F('win32_2012_release_factory', win().LibyuvFactory(
    target='Release',
    options=ninja_options,
    tests=test_targets,
    factory_properties=win_msvs_2012_factory_properties))

B('Win64 Debug (VS2012)', 'win64_2012_debug_factory',
  scheduler=scheduler_name)
F('win64_2012_debug_factory', win().LibyuvFactory(
    target='Debug_x64',
    options=ninja_options,
    tests=test_targets,
    factory_properties=win_msvs_2012_x64_factory_properties))

B('Win64 Release (VS2012)', 'win64_2012_release_factory',
  scheduler=scheduler_name)
F('win64_2012_release_factory', win().LibyuvFactory(
    target='Release_x64',
    options=ninja_options,
    tests=test_targets,
    factory_properties=win_msvs_2012_x64_factory_properties))

# Mac.
defaults['category'] = 'mac'

B('Mac32 Debug', 'mac32_debug_factory', scheduler=scheduler_name)
F('mac32_debug_factory', mac().LibyuvFactory(
    target='Debug',
    options=ninja_options,
    tests=test_targets))

B('Mac32 Release', 'mac32_release_factory', scheduler=scheduler_name)
F('mac32_release_factory', mac().LibyuvFactory(
    target='Release',
    options=ninja_options,
    tests=test_targets))

B('Mac64 Debug', 'mac64_debug_factory', scheduler=scheduler_name)
F('mac64_debug_factory', mac().LibyuvFactory(
    target='Debug',
    options=ninja_options,
    tests=test_targets,
    factory_properties={
        'gclient_env': {'GYP_DEFINES': 'host_arch=x64 target_arch=x64'},
    }))

B('Mac64 Release', 'mac64_release_factory', scheduler=scheduler_name)
F('mac64_release_factory', mac().LibyuvFactory(
    target='Release',
    options=ninja_options,
    tests=test_targets,
    factory_properties={
        'gclient_env': {'GYP_DEFINES': 'host_arch=x64 target_arch=x64'},
    }))

B('Mac Asan', 'mac_asan_factory', scheduler=scheduler_name)
F('mac_asan_factory', mac().LibyuvFactory(
    target='Release',
    options=ninja_options,
    tests=test_targets,
    factory_properties={
        'asan': True,
        'gclient_env': asan_gclient_env.copy(),
    }))

B('iOS Debug', 'ios_debug_factory', scheduler=scheduler_name)
F('ios_debug_factory', mac_ios().LibyuvFactory(
    target='Debug-iphoneos',
    options=ninja_options,
    factory_properties=mac_ios_factory_properties))

B('iOS Release', 'ios_release_factory', scheduler=scheduler_name)
F('ios_release_factory', mac_ios().LibyuvFactory(
    target='Release-iphoneos',
    options=ninja_options,
    factory_properties=mac_ios_factory_properties))

# Linux.
defaults['category'] = 'linux'

B('Linux32 Debug', 'linux32_debug_factory', scheduler=scheduler_name)
F('linux32_debug_factory', linux().LibyuvFactory(
    target='Debug',
    options=ninja_options,
    tests=test_targets,
    factory_properties={'gclient_env': {'GYP_DEFINES': 'target_arch=ia32'}}))

B('Linux32 Release', 'linux32_release_factory', scheduler=scheduler_name)
F('linux32_release_factory', linux().LibyuvFactory(
    target='Release',
    options=ninja_options,
    tests=test_targets,
    factory_properties={'gclient_env': {'GYP_DEFINES': 'target_arch=ia32'}}))

B('Linux64 Debug', 'linux64_debug_factory', scheduler=scheduler_name)
F('linux64_debug_factory', linux().LibyuvFactory(
    target='Debug',
    options=ninja_options,
    tests=test_targets))

B('Linux64 Release', 'linux64_release_factory', scheduler=scheduler_name)
F('linux64_release_factory', linux().LibyuvFactory(
    target='Release',
    options=ninja_options,
    tests=test_targets))

B('Linux Clang', 'linux_clang_factory', scheduler=scheduler_name)
F('linux_clang_factory', linux().LibyuvFactory(
    target='Debug',
    options=ninja_options + ['--compiler=clang'],
    tests=test_targets,
    factory_properties={'gclient_env': {'GYP_DEFINES': 'clang=1'}}))

B('Linux Memcheck', 'linux_memcheck_factory', scheduler=scheduler_name)
F('linux_memcheck_factory', linux().LibyuvFactory(
    target='Release',
    options=ninja_options,
    tests=test_targets,
    factory_properties={
        'needs_valgrind': True,
        'gclient_env': {'GYP_DEFINES': 'build_for_tool=memcheck'},
    }))

B('Linux Tsan', 'linux_tsan_factory', scheduler=scheduler_name)
F('linux_tsan_factory', linux().LibyuvFactory(
    target='Release',
    options=ninja_options,
    tests=test_targets,
    factory_properties={
        'needs_valgrind': True,
        'gclient_env': {'GYP_DEFINES': 'build_for_tool=tsan'},
    }))

B('Linux Asan', 'linux_asan_factory', scheduler=scheduler_name)
F('linux_asan_factory', linux().LibyuvFactory(
    target='Release',
    options=ninja_options,
    tests=test_targets,
    factory_properties={
        'asan': True,
        'gclient_env': asan_gclient_env.copy(),
    }))

# Android.
B('Android Debug', 'android_debug_factory', scheduler=scheduler_name)
F('android_debug_factory', android().ChromiumAnnotationFactory(
  target='Debug',
  annotation_script='src/build/android/buildbot/bb_run_bot.py',
  factory_properties={
      'android_bot_id': 'libyuv-main-clobber-dbg',
  }))

B('Android Release', 'android_release_factory', scheduler=scheduler_name)
F('android_release_factory', android().ChromiumAnnotationFactory(
  target='Release',
  annotation_script='src/build/android/buildbot/bb_run_bot.py',
  factory_properties={
      'android_bot_id': 'libyuv-main-clobber',
  }))

# Chrome OS.
B('Chrome OS', 'chromeos_factory', scheduler=scheduler_name)
F('chromeos_factory', linux().LibyuvFactory(
    target='Debug',
    options=ninja_options,
    tests=test_targets,
    factory_properties={'gclient_env': {'GYP_DEFINES': 'chromeos=1'}}))


def Update(c):
  helper.Update(c)
