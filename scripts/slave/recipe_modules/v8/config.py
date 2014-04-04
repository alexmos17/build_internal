# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave.recipe_config import config_item_context, ConfigGroup
from slave.recipe_config import Set, Single, Static


def BaseConfig(**_kwargs):
  shard_count = _kwargs.get('SHARD_COUNT', 1)
  shard_run = _kwargs.get('SHARD_RUN', 1)
  assert shard_count >= 1
  assert shard_run >= 1
  assert shard_run <= shard_count

  return ConfigGroup(
    # Test configuration that is the equal for all tests of a builder. It
    # might be refined later in the test runner for distinct tests.
    testing = ConfigGroup(
      flaky_step = Single(bool, required=False),
      test_args = Set(basestring),

      SHARD_COUNT = Static(shard_count),
      SHARD_RUN = Static(shard_run),
    ),
  )


config_ctx = config_item_context(BaseConfig, {}, 'v8')


@config_ctx()
def v8(c):
  pass


@config_ctx()
def isolates(c):
  c.testing.test_args.add('--isolates=on')


@config_ctx()
def nosse2(c):
  c.testing.test_args.add('--shell_flags="--noenable-sse2"')


@config_ctx()
def nosse3(c):
  c.testing.test_args.add('--shell_flags="--noenable-sse3"')


@config_ctx()
def nosse4(c):
  c.testing.test_args.add('--shell_flags="--noenable-sse4-1"')


@config_ctx()
def trybot_flavor(c):
  c.testing.flaky_step = False
  c.testing.test_args.add('--quickcheck')