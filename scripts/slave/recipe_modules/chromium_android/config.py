# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave.recipe_configs_util import config_item_context, ConfigGroup
from slave.recipe_configs_util import DictConfig, ListConfig, SimpleConfig
from slave.recipe_configs_util import StaticConfig

def BaseConfig(INTERNAL, REPO_NAME, REPO_URL, **_kwargs):
  return ConfigGroup(
    INTERNAL = StaticConfig(INTERNAL),
    REPO_NAME = StaticConfig(REPO_NAME),
    REPO_URL = StaticConfig(REPO_URL),
    target_arch = SimpleConfig(basestring, required=False, empty_val=''),
    custom_vars = DictConfig(value_type=basestring),
    extra_env = DictConfig(value_type=(basestring,int,list)),
    run_findbugs = SimpleConfig(bool, required=False, empty_val=False),
    run_lint = SimpleConfig(bool, required=False, empty_val=False),
    run_checkdeps = SimpleConfig(bool, required=False, empty_val=False)
  )


VAR_TEST_MAP = {
  'INTERNAL': [True, False],
  'REPO_NAME': ['src', 'internal'],
  'REPO_URL': ['bob_dot_org', 'mike_dot_org'],
}

def TEST_NAME_FORMAT(kwargs):
  name = 'repo-%(REPO_NAME)s-from-url-%(REPO_URL)s' % kwargs
  if kwargs['INTERNAL']:
    return name + '-internal'
  else:
    return name

config_ctx = config_item_context(BaseConfig, VAR_TEST_MAP, TEST_NAME_FORMAT)

@config_ctx(is_root=True)
def main_builder(c):
  pass

@config_ctx()
def clang_builder(c):
  if c.INTERNAL:
    c.run_findbugs = True
    c.run_lint = True
    c.run_checkdeps = True

@config_ctx()
def component_builder(c):
  pass

@config_ctx()
def x86_builder(c):
  c.target_arch = 'x86'

@config_ctx()
def klp_builder(c):
  c.extra_env = {
    'ANDROID_SDK_BUILD_TOOLS_VERSION': 'android-KeyLimePie',
    'ANDROID_SDK_ROOT': ['third_party', 'android_tools_internal', 'sdk'],
    'ANDROID_SDK_VERSION': 'KeyLimePie'
  }

@config_ctx()
def try_builder(c):
  if c.INTERNAL:
    c.run_findbugs = True
    c.run_lint = True
