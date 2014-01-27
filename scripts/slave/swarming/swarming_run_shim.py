#!/usr/bin/env python
# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Drives tests on Swarming. Both trigger and collect results.

This is the shim that is called through buildbot.
"""

import logging
import optparse
import os
import subprocess
import sys
import threading
import Queue

from common import chromium_utils
from common import find_depot_tools  # pylint: disable=W0611

from common import annotator
from slave.swarming import swarming_utils

# From depot tools/
import fix_encoding


def v0_3(
    client, swarming_server, isolate_server, priority, dimensions,
    task_name, isolated_hash, env, shards):
  """Handles swarm_client/swarming.py starting 7c543276f08.

  It was rolled in src on r237619 on 2013-11-27.
  """
  cmd = [
      sys.executable,
      os.path.join(client, 'swarming.py'),
      'run',
      '--swarming', swarming_server,
      '--isolate-server', isolate_server,
      '--priority', str(priority),
      '--shards', str(shards),
      '--task-name', task_name,
      isolated_hash,
  ]
  for name, value in dimensions.iteritems():
    if name != 'os':
      cmd.extend(('--dimension', name, value))
    else:
      # Sadly, older version of swarming.py need special handling of os.
      old_value = [
          k for k, v in swarming_utils.OS_MAPPING.iteritems() if v == value
      ]
      assert len(old_value) == 1
      cmd.extend(('--os', old_value[0]))

  # Enable profiling on the -dev server.
  if '-dev' in swarming_server:
    cmd.append('--profile')
  for name, value in env.iteritems():
    cmd.extend(('--env', name, value))
  return cmd


def v0_4(
    client, swarming_server, isolate_server, priority, dimensions,
    task_name, isolated_hash, env, shards):
  """Handles swarm_client/swarming.py starting b39e8cf08c.

  It was rolled in src on r246113 on 2014-01-21.
  """
  cmd = [
    sys.executable,
    os.path.join(client, 'swarming.py'),
    'run',
    '--swarming', swarming_server,
    '--isolate-server', isolate_server,
    '--priority', str(priority),
    '--shards', str(shards),
    '--task-name', task_name,
    isolated_hash,
  ]
  for name, value in dimensions.iteritems():
    cmd.extend(('--dimension', name, value))
  # Enable profiling on the -dev server.
  if '-dev' in swarming_server:
    cmd.append('--profile')
  for name, value in env.iteritems():
    cmd.extend(('--env', name, value))
  return cmd


def stream_process(cmd):
  """Calls process cmd and yields its output.

  This is not the most efficient nor safe way to do it but it is only meant to
  be run on linux so it should be fine. Fix if necessary.
  """
  p = subprocess.Popen(
      cmd, bufsize=1, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
  try:
    while True:
      try:
        i = p.stdout.readline()
        if i:
          if sys.platform == 'win32':
            # Instead of using universal_newlines=True which would affect
            # buffering, just convert the ending CRLF to LF. Otherwise, it
            # creates an double interline.
            if i.endswith('\r\n'):
              i = i[:-1] + '\n'
          yield i
          continue
      except OSError:
        pass
      if p.poll() is not None:
        break
    yield p.returncode
  finally:
    if p.poll() is None:
      p.kill()


def drive_one(
    client, version, swarming_server, isolate_server, priority, dimensions,
    task_name, isolated_hash, env, shards, out):
  """Executes the proper handler based on the code layout and --version support.
  """
  def send_back(l):
    out.put((task_name, l))
  if version < (0, 4):
    cmd = v0_3(
        client, swarming_server, isolate_server, priority, dimensions,
        task_name, isolated_hash, env, shards)
  else:
    cmd = v0_4(
        client, swarming_server, isolate_server, priority, dimensions,
        task_name, isolated_hash, env, shards)
  try:
    for i in stream_process(cmd):
      send_back(i)
  except Exception as e:
    send_back(e)


def drive_many(
    client, version, swarming_server, isolate_server, priority, dimensions,
    steps):
  logging.info(
      'drive_many(%s, %s, %s, %s, %s, %s, %s)',
      client, version, swarming_server, isolate_server, priority, dimensions,
      steps)
  return _drive_many(
    client, version, swarming_server, isolate_server, priority, dimensions,
    steps, Queue.Queue())


def step_name_to_cursor(x):
  """The cursor is buildbot's step name. It is only the base test name for
  simplicity.

  But the swarming task name is longer, it is
  "<name>/<dimensions>/<isolated hash>".
  """
  return x.split('/', 1)[0]


def _drive_many(
    client, version, swarming_server, isolate_server, priority, dimensions,
    steps, out):
  """Internal version, exposed so it can be hooked in test."""
  stream = annotator.AdvancedAnnotationStream(sys.stdout, False)
  for step_name in sorted(steps):
    # Seeds the step first before doing the cursors otherwise it is interleaved
    # in the logs of other steps.
    stream.seed_step(step_name)

  threads = []
  # Create the boxes in buildbot in order for consistency.
  steps_annotations = {}
  for step_name, isolated_hash in sorted(steps.iteritems()):
    env = {}
    # TODO(maruel): Propagate GTEST_FILTER.
    #if gtest_filter not in (None, '', '.', '*'):
    #  env['GTEST_FILTER'] = gtest_filter
    shards = swarming_utils.TESTS_SHARDS.get(step_name, 1)
    # This will be the key in steps_annotations.
    task_name = '%s/%s/%s' % (step_name, dimensions['os'], isolated_hash)
    t = threading.Thread(
        target=drive_one,
        args=(client, version, swarming_server, isolate_server, priority,
              dimensions, task_name, isolated_hash, env, shards, out))
    t.daemon = True
    t.start()
    threads.append(t)
    steps_annotations[task_name] = annotator.AdvancedAnnotationStep(
        sys.stdout, False)
    items = task_name.split('/', 2)
    assert step_name == items[0]
    assert step_name == step_name_to_cursor(task_name)
    # It is important data to surface through buildbot.
    stream.step_cursor(step_name)
    steps_annotations[task_name].step_text(items[1])
    steps_annotations[task_name].step_text(items[2])
  collect(stream, steps_annotations, out)
  return 0


def collect(stream, steps_annotations, out):
  last_cursor = None
  while steps_annotations:
    try:
      # Polling FTW.
      packet = out.get(timeout=1)
    except Queue.Empty:
      continue
    task_name, item = packet
    if last_cursor != task_name:
      stream.step_cursor(step_name_to_cursor(task_name))
      last_cursor = task_name
    if isinstance(item, int):
      # Signals it's completed.
      if item:
        steps_annotations[task_name].step_failure()
      steps_annotations[task_name].step_closed()
      del steps_annotations[task_name]
      last_cursor = None
    elif isinstance(item, Exception):
      print >> sys.stderr, item
      steps_annotations[task_name].step_failure()
      steps_annotations[task_name].step_close()
      del steps_annotations[task_name]
      last_cursor = None
    else:
      assert isinstance(item, str), item
      sys.stdout.write(item)
    out.task_done()


def determine_steps_to_run(isolated_hashes, default_swarming_tests, testfilter):
  """Returns a dict of test:hash for the test that should be run through
  Swarming.

  This is done by looking at the build properties to figure out what should be
  run.
  """
  logging.info(
      'determine_steps_to_run(%s, %s, %s)',
      isolated_hashes, default_swarming_tests, testfilter)
  # TODO(maruel): Support gtest filter.
  def should_run(name):
    return (
        ((name in default_swarming_tests or not default_swarming_tests) and
          'defaulttests' in testfilter) or
         (name + '_swarm' in testfilter))

  return dict(
      (name, isolated_hash)
      for name, isolated_hash in isolated_hashes.iteritems()
      if should_run(name))


def process_build_properties(options):
  """Converts build properties and factory properties into expected flags."""
  # target_os is not defined when using a normal builder, contrary to a
  # xx_swarm_triggered buildbot<->swarming builder, and it's not needed since
  # the OS match, it's defined in builder/tester configurations.
  slave_os = options.build_properties.get('target_os', sys.platform)
  priority = swarming_utils.build_to_priority(options.build_properties)
  steps = determine_steps_to_run(
      options.build_properties.get('swarm_hashes', {}),
      options.build_properties.get('run_default_swarm_tests', []),
      options.build_properties.get('testfilter', ['defaulttests']))
  return slave_os, priority, steps


def main(args):
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
  version = swarming_utils.get_version(client)
  if version < (0, 3):
    print >> sys.stderr, (
        '%s is version %s which is too old. Please run the test locally' %
        (client, '.'.join(version)))
    return 1

  parser = optparse.OptionParser(description=sys.modules[__name__].__doc__)
  parser.add_option('--verbose', action='store_true')
  parser.add_option('--swarming')
  parser.add_option('--isolate-server')
  chromium_utils.AddPropertiesOptions(parser)
  options, args = parser.parse_args(args)
  if args:
    parser.error('Unsupported args: %s' % args)
  if not options.swarming or not options.isolate_server:
    parser.error('Require both --swarming and --isolate-server')

  logging.basicConfig(level=logging.DEBUG if options.verbose else logging.ERROR)
  # Loads the other flags implicitly.
  slave_os, priority, steps = process_build_properties(options)
  logging.info('To run: %s, %s, %s', slave_os, priority, steps)
  if not steps:
    print('Nothing to trigger')
    annotator.AdvancedAnnotationStep(sys.stdout, False).step_warnings()
    return 0
  print('Selected tests:')
  print('\n'.join(' %s' % s for s in sorted(steps)))
  selected_os = swarming_utils.OS_MAPPING[slave_os]
  print('Selected OS: %s' % selected_os)
  return drive_many(
      client,
      version,
      options.swarming,
      options.isolate_server,
      priority,
      {'os': selected_os},
      steps)


if __name__ == '__main__':
  fix_encoding.fix_encoding()
  sys.exit(main(sys.argv[1:]))
