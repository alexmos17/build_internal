# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Buildbot recipe definition for the various Syzygy continuous builders.

To be tested using a command-line like:

  /build/scripts/tools/run_recipe.py syzygy/continuous
      revision=0e9f25b1098271be2b096fd1c095d6d907cf86f7
      mainname=main.client.syzygy
      "buildername=Syzygy Debug"
      subordinatename=fake_subordinate
      buildnumber=1

Places resulting output in build/subordinate/fake_subordinate.
"""

# Recipe module dependencies.
DEPS = [
  'chromium',
  'gclient',
  'platform',
  'properties',
  'syzygy',
]


# Valid continuous builders and the Syzygy configurations they load.
_BUILDERS = {'Syzygy Debug': ('syzygy', {'BUILD_CONFIG': 'Debug'}),
             'Syzygy Release': ('syzygy', {'BUILD_CONFIG': 'Release'}),
             'Syzygy Official': ('syzygy_official', {})}


def GenSteps(api):
  """Generates the sequence of steps that will be run by the subordinate."""
  buildername = api.properties['buildername']
  assert buildername in _BUILDERS

  # Configure the build environment.
  s = api.syzygy
  config, kwargs = _BUILDERS[buildername]
  s.set_config(config, **kwargs)

  # Clean up any running processes on the subordinate.
  s.taskkill()

  # Checkout and compile the project.
  s.checkout()
  s.runhooks()
  s.compile()

  # Load and run the unittests.
  unittests = s.read_unittests_gypi()
  s.run_unittests(unittests)

  build_config = api.chromium.c.BUILD_CONFIG
  if build_config == 'Release':
    s.randomly_reorder_chrome()
    s.benchmark_chrome()

  if s.c.official_build:
    assert build_config == 'Release'
    s.archive_binaries()
    s.upload_symbols()


def GenTests(api):
  """Generates an end-to-end successful test for each builder."""
  for buildername in _BUILDERS.iterkeys():
    yield api.syzygy.generate_test(api, buildername)
