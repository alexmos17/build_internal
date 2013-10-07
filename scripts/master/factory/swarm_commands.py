# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set of utilities to add commands to a buildbot factory.

This is based on commands.py and adds swarm-specific commands."""

from buildbot.steps import shell, source
from twisted.python import log

from master import chromium_step
from master.factory import commands

import config


def TestStepFilterTriggerSwarm(bStep):
  """Returns True if any swarm step is going to be run by this builder or a
  triggered one.

  This is only useful on the Try Server, where triggering the swarm_triggered
  try builder is conditional on running at least one swarm job there. Nobody
  wants email for an empty job.
  """
  return bool(commands.GetSwarmTests(bStep))


def TestStepFilterRetrieveSwarmResult(bStep):
  """Returns True if the given swarm step to get results should be run.

  It should be run if the .isolated hash was calculated.
  """
  # TODO(maruel): bStep.name[:-len('_swarm')] once the swarm retrieve results
  # steps have the _swarm suffix.
  return bStep.name in commands.GetProp(bStep, 'swarm_hashes', {})


class SwarmClientSVN(source.SVN):
  """Uses the revision specified by use_swarm_client_revision."""

  def start(self):
    """Contrary to source.Source, ignores the branch, source stamp and patch."""
    self.args['workdir'] = self.workdir
    revision = commands.GetProp(self, 'use_swarm_client_revision', None)
    self.startVC(None, revision, None)


class SwarmingClientGIT(source.Git):
  """Uses the revision specified by use_swarming_client_revision."""

  def start(self):
    """Contrary to source.Source, ignores the branch, source stamp and patch."""
    self.args['workdir'] = self.workdir
    revision = commands.GetProp(self, 'use_swarming_client_revision', None)
    self.startVC(None, revision, None)


class SwarmShellForTriggeringTests(shell.ShellCommand):
  """Triggers all the swarm jobs at once.

  All the tests will run concurrently on Swarm and individual steps will gather
  the results.

  Makes sure each triggered swarm job has the proper number of shards.

  This class can be used both on the Try Server, which supports 'testfilter' or
  on the CI, where the steps are run inconditionally.
  """
  def __init__(self, *args, **kwargs):
    self.tests = kwargs.pop('tests', [])
    assert all(t.__class__.__name__ == 'SwarmTest' for t in self.tests)
    shell.ShellCommand.__init__(self, *args, **kwargs)

  def start(self):
    """Triggers the intersection of 'swarm_hashes' build property,
    self.tests and 'testfilter' build property if set.

    'swarm_hashes' is already related to GetSwarmTests().
    """
    # Only used for pass gtest filters specified by the user via 'testfilter'.
    swarm_tests = commands.GetSwarmTests(self)
    # The 'swarm_hashes' build property has been set by the
    # CalculateIsolatedSha1s build step. It will have all the steps that can be
    # triggered. This implicitly takes account 'testfilter'.
    swarm_tests_hash_mapping = commands.GetProp(self, 'swarm_hashes', {})

    # TODO(maruel): Move more logic out into
    # scripts/slave/swarming/trigger_swarm_shim.py.
    command = self.command[:]
    for swarm_test in self.tests:
      if swarm_tests_hash_mapping.get(swarm_test.test_name):
        command.extend(
            [
              '--task',
              swarm_tests_hash_mapping[swarm_test.test_name],
              swarm_test.test_name,
              '%d' % swarm_test.shards,
              # '*' is a special value to mean no filter. This is used so '' is
              # not used, as '' may be misinterpreted by the shell, especially
              # on Windows.
              swarm_tests.get(swarm_test.test_name) or '*',
            ])
      else:
        log.msg('Given a swarm test, %s, that has no matching hash' %
                swarm_test.test_name)

    self.setCommand(command)
    shell.ShellCommand.start(self)


class SwarmCommands(commands.FactoryCommands):
  """Encapsulates methods to add swarm commands to a buildbot factory"""
  def __init__(self, *args, **kwargs):
    super(SwarmCommands, self).__init__(*args, **kwargs)
    self._swarming_client_dir = self.PathJoin('src', 'tools', 'swarming_client')

  def AddTriggerSwarmTestStep(self, swarm_server, isolation_outdir, tests,
                              doStepIf):
    assert all(t.__class__.__name__ == 'SwarmTest' for t in tests)
    command = [
      self._python,
      self.PathJoin(self._script_dir, 'swarming', 'trigger_swarm_shim.py'),
      '--swarming', swarm_server,
      '--isolate-server', isolation_outdir,
    ]
    command = self.AddBuildProperties(command)
    assert all(i for i in command), command
    self._factory.addStep(
        SwarmShellForTriggeringTests,
        name='swarm_trigger_tests',
        description='Trigger swarm steps',
        command=command,
        tests=tests,
        doStepIf=doStepIf)

  def AddGetSwarmTestStep(self, swarm_server, test_name, num_shards):
    """Adds the step to retrieve the Swarm job results asynchronously."""
    # TODO(maruel): assert test_name.endswith('_swarm') once swarm retrieve
    # results steps have _swarm suffix.
    command = [
      self._python,
      self.PathJoin(self._script_dir, 'swarming', 'get_swarm_results_shim.py'),
      '--swarming', swarm_server,
      '--shards', '%d' % num_shards,
      test_name,
    ]
    command = self.AddBuildProperties(command)

    # Swarm handles the timeouts due to no ouput being produced for 10 minutes,
    # but we don't have access to the output until the whole test is done, which
    # may take more than 10 minutes, so we increase the buildbot timeout.
    timeout = 2 * 60 * 60
    self._factory.addStep(
        shell.ShellCommand,
        name=test_name,
        description='%s Swarming' % test_name,
        command=command,
        timeout=timeout,
        doStepIf=TestStepFilterRetrieveSwarmResult)

  def AddUpdateSwarmClientStep(self):
    """Checks out swarming_client so it can be used at the right revision."""
    def doSwarmingStepIf(b):
      return bool(commands.GetProp(b, 'use_swarming_client_revision', None))
    def doSwarmStepIf(b):
      return not doSwarmingStepIf(b)

    # Emulate the path of a src/DEPS checkout, to keep things simpler.
    relpath = 'build/src/tools/swarming_client'
    url = (
        config.Master.server_url +
        config.Master.repo_root +
        '/trunk/tools/swarm_client')
    self._factory.addStep(
        SwarmClientSVN,
        svnurl=url,
        workdir=relpath,
        doStepIf=doSwarmStepIf)

    url = config.Master.git_server_url + '/external/swarming.client'
    self._factory.addStep(
        SwarmingClientGIT,
        repourl=url,
        workdir=relpath,
        doStepIf=doSwarmingStepIf)

  def AddIsolateTest(self, test_name):
    if not self._target:
      log.msg('No target specified, unable to find isolated files')
      return

    isolated_file = test_name + '.isolated'

    script_path = self.PathJoin(self._swarming_client_dir, 'isolate.py')
    slave_script_path = self.PathJoin(
        self._script_dir, 'swarming', 'isolate_shim.py'),

    args = [script_path, 'run', '--isolated', isolated_file, '--', '--no-cr']
    wrapper_args = ['--annotate=gtest', '--test-type=%s' % test_name]

    command = self.GetPythonTestCommand(slave_script_path, arg_list=args,
                                        wrapper_args=wrapper_args)
    self.AddTestStep(chromium_step.AnnotatedCommand,
                     test_name,
                     command)

  def SetupWinNetworkDrive(self, drive, network_path):
    script_path = self.PathJoin(self._script_dir, 'add_network_drive.py')

    command = [self._python, script_path, '--drive', drive,
               '--network_path', network_path]

    self._factory.addStep(
        shell.ShellCommand,
        name='setup_windows_network_storage',
        description='setup_windows_network_storage',
        descriptionDone='setup_windows_network_storage',
        command=command)
