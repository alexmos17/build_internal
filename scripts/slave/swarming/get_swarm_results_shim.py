#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Takes in a test name and retrives all the output that the swarm server
has produced for tests with that name. This is expected to be called as a
build step.
"""

import optparse
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

from common import chromium_utils
from common import find_depot_tools  # pylint: disable=W0611
from common import gtest_utils

from slave.swarming import swarming_utils

# From depot_tools/
import fix_encoding


NO_OUTPUT_FOUND = (
    'No output produced by the test, it may have failed to run.\n'
    'Showing all the output, including swarm specific output.\n'
    '\n')


def gen_shard_output(result, gtest_parser):
  """Returns output for swarm shard."""
  index = result['config_instance_index']
  machine_id = result['machine_id']
  machine_tag = result.get('machine_tag', 'unknown')

  header = (
    '\n'
    '================================================================\n'
    'Begin output from shard index %s (machine tag: %s, id: %s)\n'
    '================================================================\n'
    '\n') % (index, machine_tag, machine_id)

  # If we fail to get output, we should always mark it as an error.
  if result['output']:
    map(gtest_parser.ProcessLine, result['output'].splitlines())
    content = result['output']
  else:
    content = NO_OUTPUT_FOUND

  test_exit_codes = (result['exit_codes'] or '1').split(',')
  test_exit_code = max(int(i) for i in test_exit_codes)
  test_exit_code = test_exit_code or int(not result['output'])

  footer = (
    '\n'
    '================================================================\n'
    'End output from shard index %s (machine tag: %s, id: %s). Return %d\n'
    '================================================================\n'
  ) % (index, machine_tag, machine_id, test_exit_code)

  return header + content + footer, test_exit_code


def gen_summary_output(failed_tests, exit_code, shards_remaining):
  out = 'Summary for all the shards:\n'
  if failed_tests:
    plural = 's' if len(failed_tests) > 1 else ''
    out += '%d test%s failed, listed below:\n' % (len(failed_tests), plural)
    out += ''.join('  %s\n' % test for test in failed_tests)

  if shards_remaining:
    out += 'Not all shards were executed.\n'
    out += 'The following gtest shards weren\'t run:\n'
    out += ''.join('  %d\n' % shard_id for shard_id in shards_remaining)
    exit_code = exit_code or 1
  elif not failed_tests:
    out += 'All tests passed.'
  return out, exit_code


def v0(client, options, test_name):
  """This code supports all the earliest versions of swarm_client.

  This is before --version was added.
  """
  sys.path.insert(0, client)
  import swarm_get_results  # pylint: disable=F0401

  timeout = swarm_get_results.DEFAULT_SHARD_WAIT_TIME
  test_keys = swarm_get_results.get_test_keys(
      options.swarming, test_name, timeout)
  if not test_keys:
    print >> sys.stderr, 'No test keys to get results with.'
    return 1

  if options.shards == -1:
    options.shards = len(test_keys)
  elif len(test_keys) < options.shards:
    print >> sys.stderr, ('Warning: Test should have %d shards, but only %d '
                          'test keys were found' % (options.shards,
                                                    len(test_keys)))

  gtest_parser = gtest_utils.GTestLogParser()
  exit_code = None
  shards_remaining = range(len(test_keys))
  first_result = True
  for index, result in swarm_get_results.yield_results(
      options.swarming, test_keys, timeout, None):
    assert index == result['config_instance_index']
    if first_result and result['num_config_instances'] != len(test_keys):
      # There are more test_keys than actual shards.
      shards_remaining = shards_remaining[:result['num_config_instances']]
    shards_remaining.remove(index)
    first_result = False
    output, test_exit_code = gen_shard_output(result, gtest_parser)
    print output
    exit_code = max(exit_code, test_exit_code)

  output, exit_code = gen_summary_output(
      gtest_parser.FailedTests(),
      exit_code,
      shards_remaining)
  print output
  return exit_code


def determine_version_and_run_handler(client, options, test_name):
  """Executes the proper handler based on the code layout and --version
  support.
  """
  # TODO(maruel): Determine version when needed.
  return v0(client, options, test_name)


def process_build_properties(options, name):
  """Converts build properties and factory properties into expected flags."""
  taskname = '%s-%s-%s' % (
      options.build_properties.get('buildername'),
      options.build_properties.get('buildnumber'),
      name,
  )
  return taskname


def main():
  """Note: this is solely to run the current master's code and can totally
  differ from the underlying script flags.

  To update these flags:
  - Update the following code to support both the previous flag and the new
    flag.
  - Change scripts/master/factory/swarm_commands.py to pass the new flag.
  - Restart all the masters using swarming.
  - Remove the old flag from this code.
  """
  client = swarming_utils.find_client(os.getcwd())
  if not client:
    print >> sys.stderr, 'Failed to find swarm(ing)_client'
    return 1

  parser = optparse.OptionParser()
  parser.add_option('-u', '--swarming', help='Swarm server')
  parser.add_option(
      '-s', '--shards', type='int', default=-1, help='Number of shards')
  chromium_utils.AddPropertiesOptions(parser)
  (options, args) = parser.parse_args()
  options.swarming = options.swarming.rstrip('/')

  if not args:
    parser.error('Must specify one test name.')
  elif len(args) > 1:
    parser.error('Must specify only one test name.')
  if options.build_properties:
    # Loads the other flags implicitly.
    task_name = process_build_properties(options, args[0])
  else:
    task_name = args[0]
  return determine_version_and_run_handler(client, options, task_name)


if __name__ == '__main__':
  fix_encoding.fix_encoding()
  sys.exit(main())
