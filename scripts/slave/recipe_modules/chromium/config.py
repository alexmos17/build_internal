# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave.recipe_config import config_item_context, ConfigGroup
from slave.recipe_config import Dict, Single, Static, Set, BadConf
from slave.recipe_config_types import Path

# Because of the way that we use decorators, pylint can't figure out the proper
# type signature of functions annotated with the @config_ctx decorator.
# pylint: disable=E1123

HOST_PLATFORMS = ('linux', 'win', 'mac')
TARGET_PLATFORMS = HOST_PLATFORMS + ('ios', 'android', 'chromeos')
HOST_TARGET_BITS = (32, 64)
HOST_ARCHS = ('intel',)
TARGET_ARCHS = HOST_ARCHS + ('arm', 'mips')
BUILD_CONFIGS = ('Release', 'Debug')

def check(val, potentials):
  assert val in potentials
  return val

# Schema for config items in this module.
def BaseConfig(HOST_PLATFORM, HOST_ARCH, HOST_BITS,
               TARGET_PLATFORM, TARGET_ARCH, TARGET_BITS,
               BUILD_CONFIG, **_kwargs):
  equal_fn = lambda tup: ('%s=%s' % tup)
  return ConfigGroup(
    compile_py = ConfigGroup(
      default_targets = Set(basestring),
      build_tool = Single(basestring),
      compiler = Single(basestring, required=False),
    ),
    gyp_env = ConfigGroup(
      GYP_CROSSCOMPILE = Single(int, jsonish_fn=str, required=False),
      GYP_DEFINES = Dict(equal_fn, ' '.join, (basestring,int,Path)),
      GYP_GENERATORS = Set(basestring, ','.join),
      GYP_GENERATOR_FLAGS = Dict(equal_fn, ' '.join, (basestring,int)),
      GYP_MSVS_VERSION = Single(basestring, required=False),
    ),
    build_dir = Single(Path),

    # Some platforms do not have a 1:1 correlation of BUILD_CONFIG to what is
    # passed as --target on the command line.
    build_config_fs = Single(basestring),

    BUILD_CONFIG = Static(check(BUILD_CONFIG, BUILD_CONFIGS)),

    HOST_PLATFORM = Static(check(HOST_PLATFORM, HOST_PLATFORMS)),
    HOST_ARCH = Static(check(HOST_ARCH, HOST_ARCHS)),
    HOST_BITS = Static(check(HOST_BITS, HOST_TARGET_BITS)),

    TARGET_PLATFORM = Static(check(TARGET_PLATFORM, TARGET_PLATFORMS)),
    TARGET_ARCH = Static(check(TARGET_ARCH, TARGET_ARCHS)),
    TARGET_BITS = Static(check(TARGET_BITS, HOST_TARGET_BITS)),
  )

TEST_FORMAT = (
  '%(BUILD_CONFIG)s-'
  '%(HOST_PLATFORM)s.%(HOST_ARCH)s.%(HOST_BITS)s'
  '-to-'
  '%(TARGET_PLATFORM)s.%(TARGET_ARCH)s.%(TARGET_BITS)s'
)

# Used by the test harness to inspect and generate permutations for this
# config module.  {varname -> [possible values]}
VAR_TEST_MAP = {
  'HOST_PLATFORM':   HOST_PLATFORMS,
  'HOST_ARCH':       HOST_ARCHS,
  'HOST_BITS':       HOST_TARGET_BITS,

  'TARGET_PLATFORM': TARGET_PLATFORMS,
  'TARGET_ARCH':     TARGET_ARCHS,
  'TARGET_BITS':     HOST_TARGET_BITS,

  'BUILD_CONFIG':    BUILD_CONFIGS,
}
config_ctx = config_item_context(BaseConfig, VAR_TEST_MAP, TEST_FORMAT)


@config_ctx(is_root=True)
def BASE(c):
  host_targ_tuples = [(c.HOST_PLATFORM, c.HOST_ARCH, c.HOST_BITS),
                      (c.TARGET_PLATFORM, c.TARGET_ARCH, c.TARGET_BITS)]

  for (plat, arch, bits) in host_targ_tuples:
    if plat == 'ios':
      if arch != 'arm' or bits != 32:
        raise BadConf('iOS only supports arm/32')
    elif plat in ('win', 'mac'):
      if arch != 'intel':
        raise BadConf('%s arch is not supported on %s' % (arch, plat))
    elif plat in ('chromeos', 'android', 'linux'):
      pass  # no arch restrictions
    else:  # pragma: no cover
      assert False, "Not covering a platform: %s" % plat

  potential_platforms = {
    # host -> potential target platforms
    'win':   ('win',),
    'mac':   ('mac', 'ios'),
    'linux': ('linux', 'chromeos', 'android'),
  }.get(c.HOST_PLATFORM)

  if not potential_platforms:  # pragma: no cover
    raise BadConf('Cannot build on "%s"' % c.HOST_PLATFORM)

  if c.TARGET_PLATFORM not in potential_platforms:
    raise BadConf('Can not compile "%s" on "%s"' %
                  (c.TARGET_PLATFORM, c.HOST_PLATFORM))

  if c.HOST_BITS < c.TARGET_BITS:
    raise BadConf('host bits < targ bits')

  c.build_config_fs = c.BUILD_CONFIG
  if c.HOST_PLATFORM == 'win':
    if c.TARGET_BITS == 64:
      # Windows requires 64-bit builds to be in <dir>_x64.
      c.build_config_fs = c.BUILD_CONFIG + '_x64'
      c.gyp_env.GYP_MSVS_VERSION = '2012'
      c.gyp_env.GYP_DEFINES['target_arch'] = 'x64'
    else:
      c.gyp_env.GYP_MSVS_VERSION = '2010'

  if c.BUILD_CONFIG == 'Release':
    static_library(c, final=False)
  elif c.BUILD_CONFIG == 'Debug':
    shared_library(c, final=False)
  else:  # pragma: no cover
    raise BadConf('Unknown build config "%s"' % c.BUILD_CONFIG)

@config_ctx(group='builder')
def ninja(c):
  c.gyp_env.GYP_GENERATORS.add('ninja')
  c.compile_py.build_tool = 'ninja'
  c.build_dir = Path('[CHECKOUT]', 'out')

@config_ctx(group='builder')
def msvs(c):
  if c.HOST_PLATFORM != 'win':
    raise BadConf('can not use msvs on "%s"' % c.HOST_PLATFORM)
  c.gyp_env.GYP_GENERATORS.add('msvs')
  c.gyp_env.GYP_GENERATOR_FLAGS['msvs_error_on_missing_sources'] = 1
  c.compile_py.build_tool = 'msvs'
  c.build_dir = Path('[CHECKOUT]', 'build')

@config_ctx(group='builder')
def xcodebuild(c):
  if c.HOST_PLATFORM != 'mac':
    raise BadConf('can not use xcodebuild on "%s"' % c.HOST_PLATFORM)
  c.gyp_env.GYP_GENERATORS.add('xcodebuild')

@config_ctx(group='compiler')
def clang(c):
  c.compile_py.compiler = 'clang'
  c.gyp_env.GYP_DEFINES['clang'] = 1

@config_ctx(group='compiler')
def default_compiler(_c):
  pass

@config_ctx(deps=['compiler', 'builder'], group='distributor')
def goma(c):
  if c.compile_py.build_tool == 'msvs':  # pragma: no cover
    raise BadConf('goma doesn\'t work with msvs')

  # TODO(iannucci): support clang and jsonclang
  if not c.compile_py.compiler:
    c.compile_py.compiler = 'goma'
  elif c.compile_py.compiler == 'clang':
    c.compile_py.compiler = 'goma-clang'
  else:  # pragma: no cover
    raise BadConf('goma config dosen\'t understand %s' % c.compile_py.compiler)

  if c.TARGET_PLATFORM == 'win':
    fastbuild(c)
    pch(c, invert=True)

@config_ctx()
def pch(c, invert=False):
  if c.TARGET_PLATFORM == 'win':
    c.gyp_env.GYP_DEFINES['chromium_win_pch'] = int(not invert)

@config_ctx()
def dcheck(c, invert=False):
  c.gyp_env.GYP_DEFINES['dcheck_always_on'] = int(not invert)

@config_ctx()
def fastbuild(c, invert=False):
  c.gyp_env.GYP_DEFINES['fastbuild'] = int(not invert)

@config_ctx(group='link_type')
def shared_library(c):
  c.gyp_env.GYP_DEFINES['component'] = 'shared_library'

@config_ctx(group='link_type')
def static_library(c):
  c.gyp_env.GYP_DEFINES['component'] = 'static_library'

@config_ctx()
def trybot_flavor(c):
  fastbuild(c, optional=True)
  dcheck(c, optional=True)

#### 'Full' configurations
@config_ctx(includes=['ninja', 'default_compiler', 'goma'])
def chromium(c):
  c.compile_py.default_targets = ['All', 'chromium_builder_tests']

@config_ctx(includes=['ninja', 'clang', 'goma'])
def chromium_clang(c):
  c.compile_py.default_targets = ['All', 'chromium_builder_tests']

@config_ctx(includes=['chromium'])
def blink(c):
  c.compile_py.default_targets = ['blink_tests']

@config_ctx(includes=['chromium_clang'])
def blink_clang(c):
  c.compile_py.default_targets = ['blink_tests']
