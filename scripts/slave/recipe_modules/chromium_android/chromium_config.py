# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave.recipe_config_types import Path
from slave import recipe_config

from RECIPE_MODULES.chromium import CONFIG_CTX

@CONFIG_CTX(includes=['ninja', 'static_library'],
            config_vars={'TARGET_ARCH': 'arm', 'TARGET_BITS': 32,
                         'BUILD_CONFIG': 'Debug'})
def base_config(c):
  c.compile_py.default_targets=[]
  gyp_defs = c.gyp_env.GYP_DEFINES
  gyp_defs['fastbuild'] = 1
  gyp_defs['OS'] = 'android'

  if c.HOST_PLATFORM != 'linux':
    raise recipe_config.BadConf('Can only build android on linux.')

@CONFIG_CTX(includes=['base_config', 'default_compiler', 'goma'])
def main_builder(c):
  if c.TARGET_ARCH != 'arm':
    raise recipe_config.BadConf(
      'Cannot target arm with TARGET_ARCH == %s' % c.TARGET_ARCH)

@CONFIG_CTX(includes=['base_config', 'clang', 'goma'])
def clang_builder(c):
  c.gyp_env.GYP_DEFINES['component'] = 'shared_library'
  c.gyp_env.GYP_DEFINES['asan'] = 1
  c.gyp_env.GYP_DEFINES['use_allocator'] = 'none'

@CONFIG_CTX(includes=['base_config', 'clang', 'goma'])
def clang_release_builder(c):
  c.gyp_env.GYP_DEFINES['component'] = 'shared_library'
  c.gyp_env.GYP_DEFINES['asan'] = 1
  c.gyp_env.GYP_DEFINES['use_allocator'] = 'none'
  c.compile_py.default_targets = ['chrome_apk']

@CONFIG_CTX(includes=['clang_release_builder','android_l'])
def clang_release_builder_l(c):
  pass

@CONFIG_CTX(includes=['main_builder'])
def component_builder(c):
  c.gyp_env.GYP_DEFINES['component'] = 'shared_library'

@CONFIG_CTX(includes=['base_config', 'default_compiler', 'goma'],
            config_vars={'TARGET_ARCH': 'intel'})
def x86_builder(c):
  if c.TARGET_ARCH != 'intel':
    raise recipe_config.BadConf(
      'Cannot target x86 with TARGET_ARCH == %s' % c.TARGET_ARCH)

@CONFIG_CTX(includes=['base_config', 'default_compiler'],
            config_vars={'TARGET_ARCH': 'mipsel'})
def mipsel_builder(c):
  if c.TARGET_ARCH != 'mipsel':
    raise recipe_config.BadConf('I dunno what to put in a mips builder!')

@CONFIG_CTX(includes=['main_builder'])
def dartium_builder(c):
  c.compile_py.default_targets=['chrome_apk', 'content_shell_apk']

@CONFIG_CTX()
def cronet_builder(c):
  c.gyp_env.GYP_DEFINES['disable_file_support'] = 1
  c.gyp_env.GYP_DEFINES['disable_ftp_support'] = 1
  c.gyp_env.GYP_DEFINES['enable_websockets'] = 0
  c.gyp_env.GYP_DEFINES['use_icu_alternatives_on_android'] = 1
  c.compile_py.clobber = True
  c.compile_py.default_targets=['cronet_package',
                                'cronet_sample_test_apk',
                                'cronet_test_instrumentation_apk']

@CONFIG_CTX()
def android_l(c):
  gyp_defs = c.gyp_env.GYP_DEFINES
  gyp_defs['android_sdk_build_tools_version'] = 'android-5.0'
  gyp_defs['android_sdk_version'] = '5.0'
  gyp_defs['android_sdk_root'] = Path(
    '[CHECKOUT]', 'third_party', 'android_tools_internal', 'sdk')

@CONFIG_CTX(includes=['main_builder', 'android_l'])
def arm_l_builder(c):
  pass

@CONFIG_CTX(includes=['arm_l_builder'],
            config_vars={'BUILD_CONFIG': 'Release'})
def arm_l_builder_rel(c):
  pass

@CONFIG_CTX(includes=['base_config', 'default_compiler', 'goma'],
            config_vars={'TARGET_ARCH': 'intel', 'TARGET_BITS': 64})
def x64_builder(c):
  if c.TARGET_ARCH != 'intel' or c.TARGET_BITS != 64:
    raise recipe_config.BadConf(
      'Cannot target x64 with TARGET_ARCH == %s, TARGET_BITS == %d'
       % (c.TARGET_ARCH, c.TARGET_BITS))

@CONFIG_CTX(includes=['base_config', 'default_compiler', 'goma'])
def arm64_builder(c):
  gyp_defs = c.gyp_env.GYP_DEFINES
  gyp_defs['OS'] = 'android'
  gyp_defs['target_arch'] = 'arm64'

@CONFIG_CTX(includes=['arm64_builder'],
            config_vars={'BUILD_CONFIG': 'Release'})
def arm64_builder_rel(c):
  pass

@CONFIG_CTX(includes=['main_builder'])
def try_builder(c):
  pass

@CONFIG_CTX(includes=['x86_builder'])
def x86_try_builder(c):
  pass

@CONFIG_CTX(includes=['base_config'])
def tests_base(c):
  pass

@CONFIG_CTX(includes=['arm64_builder_rel'])
def tests_arm64(c):
  pass

@CONFIG_CTX(includes=['tests_base'])
def main_tests(c):
  pass

@CONFIG_CTX(includes=['tests_base'])
def clang_tests(c):
  pass

@CONFIG_CTX(includes=['tests_base'])
def enormous_tests(c):
  pass

@CONFIG_CTX(includes=['tests_base'])
def try_instrumentation_tests(c):
  pass

@CONFIG_CTX(includes=['x86_builder'])
def x86_try_instrumentation_tests(c):
  pass

@CONFIG_CTX(includes=['main_builder'],
            config_vars={'BUILD_CONFIG': 'Debug'})
def coverage_builder_tests(c):
  gyp_defs = c.gyp_env.GYP_DEFINES
  gyp_defs['emma_coverage'] = 1
  gyp_defs['emma_filter'] = 'com.google.android.apps.chrome.*'

@CONFIG_CTX(includes=['main_builder'])
def oilpan_builder(c):
  gyp_defs = c.gyp_env.GYP_DEFINES
  gyp_defs['enable_oilpan'] = 1

# TODO(zty): figure out what perf builder really wants and use that instead.
# e.g. official
@CONFIG_CTX(includes=['main_builder'])
def perf(c):
  gyp_defs = c.gyp_env.GYP_DEFINES
  gyp_defs['branding'] = 'Chrome'
  gyp_defs['buildtype'] = 'Official'

@CONFIG_CTX(includes=['main_builder'])
def webview_perf(c):
  gyp_defs = c.gyp_env.GYP_DEFINES
  gyp_defs['android_webview_telemetry_build'] = 1
