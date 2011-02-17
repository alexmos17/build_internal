# Copyright (c) 2011 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Set of utilities to add commands to a buildbot factory (BuildFactory).

All the utility functions to add steps to a build factory here are not
project-specific. See the other *_commands.py for project-specific commands.
"""

import ntpath
import posixpath
import re

from buildbot.locks import SlaveLock
from buildbot.process.properties import WithProperties
from buildbot.status.builder import SUCCESS
from buildbot.steps import shell

from common import chromium_utils
from master import chromium_step
from master.log_parser import cl_command
from master.log_parser import gtest_command
from master.log_parser import retcode_command
from master.optional_arguments import ListProperties

import config


# Performance step utils.
def CreatePerformanceStepClass(
    log_processor_class, report_link=None, output_dir=None,
    factory_properties=None, perf_name=None, test_name=None,
    command_class=None):
  """Returns ProcessLogShellStep class.

  Args:
    log_processor_class: class that will be used to process logs. Normally
      should be a subclass of process_log.PerformanceLogProcessor.
    report_link: URL that will be used as a link to results. If None,
      result won't be written into file.
    output_dir: directory where the log processor will write the results.
    command_class: command type to run for this step. Normally this will be
      chromium_step.ProcessLogShellStep.
  """
  factory_properties = factory_properties or {}
  command_class = command_class or chromium_step.ProcessLogShellStep
  # We create a log-processor class using
  # chromium_utils.InitializePartiallyWithArguments, which uses function
  # currying to create classes that have preset constructor arguments.
  # This serves two purposes:
  # 1. Allows the step to instantiate its log processor without any
  #    additional parameters;
  # 2. Creates a unique log processor class for each individual step, so
  # they can keep state that won't be shared between builds
  log_processor_class = chromium_utils.InitializePartiallyWithArguments(
      log_processor_class, report_link=report_link, output_dir=output_dir,
      factory_properties=factory_properties, perf_name=perf_name,
      test_name=test_name)
  # Similarly, we need to allow buildbot to create the step itself without
  # using additional parameters, so we create a step class that already
  # knows which log_processor to use.
  return chromium_utils.InitializePartiallyWithArguments(
      command_class, log_processor_class=log_processor_class)


class FactoryCommands(object):
  # Base URL for performance test results.
  PERF_BASE_URL = config.Master.perf_base_url
  PERF_REPORT_URL_SUFFIX = config.Master.perf_report_url_suffix

  # Directory in which to save perf output data files.
  PERF_OUTPUT_DIR = config.Master.perf_output_dir

  # Use this to prevent steps which cannot be run on the same
  # slave from being done together (in the case where slaves are
  # shared by multiple builds).
  slave_exclusive_lock = SlaveLock('slave_exclusive', maxCount=1)

  # --------------------------------------------------------------------------
  # PERF TEST SETTINGS
  # In each mapping below, the first key is the target and the second is the
  # perf_id. The value is the directory name in the results URL.

  # Configuration of most tests.
  PERF_TEST_MAPPINGS = {
    'Release': {
      'chromium-linux-targets': 'linux-targets',
      'chromium-mac-targets': 'mac-targets',
      'chromium-rel-xp': 'xp-release',
      'chromium-rel-xp-dual': 'xp-release-dual-core',
      'chromium-rel-xp-single': 'xp-release-single-core',
      'chromium-rel-vista-dual': 'vista-release-dual-core',
      'chromium-rel-vista-single': 'vista-release-single-core',
      'chromium-rel-vista-dual-v8': 'vista-release-v8-latest',
      'chromium-rel-vista-webkit': 'vista-release-webkit-latest',
      'chromium-rel-linux-webkit': 'linux-release-webkit-latest',
      'chromium-rel-mac': 'mac-release',
      'chromium-rel-mac5': 'mac-release-10.5',
      'chromium-rel-mac6': 'mac-release-10.6',
      'chromium-rel-mac5-v8': 'mac-release-10.5-v8-latest',
      'chromium-rel-mac6-v8': 'mac-release-10.6-v8-latest',
      'chromium-rel-mac6-webkit': 'mac-release-10.6-webkit-latest',
      'chromium-rel-linux': 'linux-release',
      'chromium-rel-linux-64': 'linux-release-64',
      'chromium-rel-linux-hardy': 'linux-release-hardy',
      'chromium-rel-linux-hardy-lowmem': 'linux-release-lowmem',
      'chromium-win-targets': 'win-targets',
      'o3d-mac-experimental': 'o3d-mac-experimental',
      'o3d-win-experimental': 'o3d-win-experimental',
      'chromium-rel-vista-memory': 'vista-release-memory',
      'chromium-rel-linux-memory': 'linux-release-memory',
      'chromium-rel-mac-memory': 'mac-release-memory',
      'chromium-rel-frame': 'win-release-chrome-frame',
      'chrome-win-beta': 'win-beta',
      'chrome-linux32-beta': 'linux32-beta',
      'chrome-linux64-beta': 'linux64-beta',
      'chrome-mac-beta': 'mac-beta',
      'chrome-win-stable': 'win-stable',
      'chrome-linux32-stable': 'linux32-stable',
      'chrome-linux64-stable': 'linux64-stable',
      'chrome-mac-stable': 'mac-stable',
      'nacl-lucid64-spec-x86': 'nacl-lucid64-spec-x86',
      'nacl-lucid64-spec-arm': 'nacl-lucid64-spec-arm',
      'nacl-lucid64-spec-trans': 'nacl-lucid64-spec-trans',
    },
    'Debug': {
      'chromium-dbg-linux': 'linux-debug',
      'chromium-dbg-mac': 'mac-debug',
      'chromium-dbg-xp': 'xp-debug',
      'chromium-dbg-linux-try': 'linux-try-debug',
    },
  }

  def __init__(self, factory=None, target=None, build_dir=None,
               target_platform=None):
    """Initializes the SlaveCommands class.
    Args:
      factory: BuildFactory to configure.
      target: Build configuration, case-sensitive; probably 'Debug' or
          'Release'
      build_dir: name of the directory within the buildbot working directory
        in which the solution, Debug, and Release directories are found.
      target_platform: Slave's OS.
    """

    self._factory = factory
    self._target = target
    self._build_dir = build_dir
    self._target_platform = target_platform

    # Starting from e.g. C:\b\build\slave\build_slave_path\build, find
    # C:\b\build\scripts\slave.
    self._script_dir = self.PathJoin('..', '..', '..', 'scripts', 'slave')

    self._perl = self.GetExecutableName('perl')

    if self._target_platform == 'win32':
      # Steps run using a separate copy of python.exe, so it can be killed at
      # the start of a build. But the kill_processes (taskkill) step has to use
      # the original python.exe, or it kills itself.
      self._python = 'python_slave'
    else:
      self._python = 'python'

    self.working_dir = 'build'
    self._repository_root = 'src'

    self._kill_tool = self.PathJoin(self._script_dir, 'kill_processes.py')
    self._compile_tool = self.PathJoin(self._script_dir, 'compile.py')
    self._test_tool = self.PathJoin(self._script_dir, 'runtest.py')
    self._zip_tool = self.PathJoin(self._script_dir, 'zip_build.py')
    self._extract_tool = self.PathJoin(self._script_dir, 'extract_build.py')
    # TODO(nsylvain): Fix redundant 'slavelastic' in path.
    self._slavelastic_tool = self.PathJoin(self._script_dir, '..',
                                           'slavelastic', 'slavelastic',
                                           'slavelastic', 'client',
                                           'distribute.py')
    self._resource_sizes_tool = self.PathJoin(self._script_dir,
                                              'resource_sizes.py')
    self._update_clang_tool = self.PathJoin(
        self._repository_root, 'tools', 'clang', 'scripts', 'update.sh')

    # chrome_staging directory, relative to the build directory.
    self._staging_dir = self.PathJoin('..', 'chrome_staging')

  # Util methods.
  def GetExecutableName(self, executable):
    """The executable name must be executable plus '.exe' on Windows, or else
    just the test name."""
    if self._target_platform == 'win32':
      return executable + '.exe'
    return executable

  def PathJoin(self, *args):
    if self._target_platform == 'win32':
      return ntpath.normpath(ntpath.join(*args))
    else:
      return posixpath.normpath(posixpath.join(*args))


  # Basic commands
  def GetTestCommand(self, executable, arg_list=None):
    cmd = [self._python, self._test_tool,
           '--target', self._target,
           '--build-dir', self._build_dir,
           self.GetExecutableName(executable)]

    if arg_list is not None:
      cmd.extend(arg_list)
    return cmd

  def AddBuildProperties(self, cmd=None):
    """Adds a WithProperties() call with build properties to cmd."""
    # pylint: disable=R0201
    cmd = cmd or []

    # Create a WithProperties format string that includes build properties.
    # Don't add blamelist since it can contain single quotes and we don't have
    # access to the rendered string to convert it to the correct JSON format
    # before sending it to the slave.
    wp_strings = []
    for prop in ['branch', 'buildername', 'buildnumber', 'got_revision',
                 'revision', 'scheduler', 'slavename']:
      wp_strings.append('"%s": "%%(%s:-)s"' % (prop, prop))
    cmd.append(WithProperties('--build-properties={' + ', '.join(wp_strings) +
                              '}'))
    return cmd

  def AddFactoryProperties(self, factory_properties, cmd=None):
    """Adds factory properties to cmd."""
    # pylint: disable=R0201
    cmd = cmd or []
    factory_properties = factory_properties or {}

    fpkeys = factory_properties.keys()
    fpkeys.sort()
    fp_strings = []
    for prop in fpkeys:
      value = str(factory_properties[prop])
      value = value.replace('"', '\\"')
      fp_strings.append('"%s": "%s"' % (prop, value))
    cmd.append('--factory-properties={' + ', '.join(fp_strings) + '}')
    return cmd

  def AddTestStep(self, command_class, test_name, test_command,
                  test_description='', timeout=600, workdir=None, env=None,
                  locks=None, halt_on_failure=False, do_step_if=True):
    """Adds a step to the factory to run a test.

    Args:
      command_class: the command type to run, such as shell.ShellCommand or
          gtest_command.GTestCommand
      test_name: a string describing the test, used to build its logfile name
          and its descriptions in the waterfall display
      timeout: the buildbot timeout for the test, in seconds.  If it doesn't
          produce any output to stdout or stderr for this many seconds,
          buildbot will cancel it and call it a failure.
      test_command: the command list to run
      test_description: an auxiliary description to be appended to the
        test_name in the buildbot display; for example, ' (single process)'
      workdir: directory where the test executable will be launched. If None,
        step will use default directory.
      env: dictionary with environmental variable key value pairs that will be
        set or overridden before launching the test executable. Does not do
        anything if 'env' is None.
      locks: any locks to acquire for this test
      halt_on_failure: whether the current build should halt if this step fails
    """
    self._factory.addStep(
        command_class,
        name=test_name,
        timeout=timeout,
        doStepIf=do_step_if,
        workdir=workdir,
        env=env,
        # TODO(bradnelson): FIXME
        #locks=locks,
        description='running %s%s' % (test_name, test_description),
        descriptionDone='%s%s' % (test_name, test_description),
        haltOnFailure=halt_on_failure,
        command=test_command)

  @staticmethod
  def GTestStepFilter(bStep):
    """Examines the 'testfilters' property of the build and determines if
    the step should run; True for yes."""
    bStep.setProperty('gtest_filter', None, "Factory")
    filters = bStep.build.getProperties().getProperty('testfilters')
    if not filters:
      return True

    for testfilter in filters:
      if testfilter == bStep.name:
        return True
      if testfilter.startswith("%s:" % bStep.name):
        bStep.setProperty('gtest_filter', "--gtest_filter=%s" %
                          testfilter.split(':', 1)[1], "Scheduler")
        return True
    return False

  def AddBasicGTestTestStep(self, test_name, factory_properties=None,
                            description='', arg_list=None, total_shards=None,
                            shard_index=None, parallel=False):
    """Adds a step to the factory to run the gtest tests.

    Args:
      total_shards: Number of shards to split this test into.
      shard_index: Shard to run.  Must be between 1 and total_shards.
      generate_gtest_json: generate JSON results file after running the tests.
    """
    factory_properties = factory_properties or {}
    generate_json = factory_properties.get('generate_gtest_json')

    if not arg_list:
      arg_list = []
    arg_list = arg_list[:]

    cmd = [self._python, self._test_tool,
           '--target', self._target,
           '--build-dir', self._build_dir]

    if generate_json:
      # test_result_dir (-o) specifies where we put the JSON output locally
      # on slaves.
      test_result_dir = 'gtest-results/%s' % test_name
      cmd.extend(['--generate-json-file',
                  '-o', test_result_dir,
                  '--test-type', test_name,
                  '--build-number', WithProperties("%(buildnumber)s"),
                  '--builder-name', WithProperties("%(buildername)s"),])

    if total_shards and shard_index:
      cmd.extend(['--total-shards', str(total_shards),
                  '--shard-index', str(shard_index)])

    if parallel:
      cmd.extend(['--parallel'])

    cmd.append(self.GetExecutableName(test_name))

    arg_list.append('--gtest_print_time')
    arg_list.append(WithProperties("%(gtest_filter)s"))
    cmd.extend(arg_list)

    self.AddTestStep(gtest_command.GTestCommand, test_name, ListProperties(cmd),
                     description, do_step_if=self.GTestStepFilter)

  def AddSlavelasticTestStep(self, test_name, factory_properties=None,
                             timeout=300):
    """Adds a step to the factory to run the slavelastic tests."""
    manifest_file = '%s.%s.manifest' % (test_name, self._target_platform)
    manifest_path = self.PathJoin('src', 'manifest', manifest_file)
    cmd = [self._python, self._slavelastic_tool, manifest_path,
           '--timeout', timeout]

    self.AddTestStep(gtest_command.GTestCommand, test_name, test_command=cmd)

  def AddBasicShellStep(self, test_name, timeout=600, arg_list=None):
    """Adds a step to the factory to run a simple shell test with standard
    defaults.
    """
    self.AddTestStep(shell.ShellCommand, test_name, timeout=timeout,
                     test_command=self.GetTestCommand(test_name,
                                                      arg_list=arg_list))

  # GClient related commands.
  def AddSvnKillStep(self):
    """Adds a step to the factory to kill svn.exe. Windows-only."""
    self._factory.addStep(shell.ShellCommand, description='svnkill',
                          timeout=60,
                          workdir='',  # The build subdir may not exist yet.
                          command=[r'%WINDIR%\system32\taskkill',
                                   '/f', '/im', 'svn.exe',
                                   '||', 'set', 'ERRORLEVEL=0'])

  def AddUpdateScriptStep(self):
    """Adds a step to the factory to update the script folder."""
    # This will be run in the '..' directory to udpate the slave's own script
    # checkout.
    command = [chromium_utils.GetGClientCommand(self._target_platform),
               'sync', '--verbose']
    self._factory.addStep(shell.ShellCommand,
                          description='update scripts',
                          locks=[self.slave_exclusive_lock],
                          timeout=60,
                          workdir='..',
                          command=command)

  def AddUpdateStep(self, gclient_spec, env=None, timeout=None,
                    sudo_for_remove=False, gclient_deps=None,
                    gclient_nohooks=False):
    """Adds a step to the factory to update the workspace."""
    if env is None:
      env = {}
    env['DEPOT_TOOLS_UPDATE'] = '0'
    if timeout is None:
      # svn timeout is 2 min; we allow 5
      timeout = 60*5
    self._factory.addStep(chromium_step.GClient,
                          gclient_spec=gclient_spec,
                          gclient_deps=gclient_deps,
                          gclient_nohooks=gclient_nohooks,
                          workdir=self.working_dir,
                          mode='update',
                          env=env,
                          locks=[self.slave_exclusive_lock],
                          retry=(60*5, 4),  # Try 4+1=5 more times, 5 min apart
                          timeout=timeout,
                          sudo_for_remove=sudo_for_remove,
                          rm_timeout=60*15) # The step can take a long time.

  def AddClobberTreeStep(self, gclient_spec, env=None, timeout=None,
                         gclient_deps=None, gclient_nohooks=False):
    """ This is not for pressing 'clobber' on the waterfall UI page. This is
        for clobbering all the sources. Using mode='clobber' causes the entire
        working directory to get moved aside (to build.dead) --OR-- if
        build.dead already exists, it deletes build.dead. Strange, but true.
        See GClient.doClobber() (for move vs. delete logic) or Gclient.start()
        (for mode='clobber' trigger) in chromium_commands.py.

        In theory, this means we can have a ClobberTree step at the beginning of
        a build to quickly move the existing workdir and do a full clean
        checkout. Then, if we add the same step at the end of a build, it will
        delete the moved-out-of-the-way directory. Presuming neither step fails
        or times out, this allows a builder to pull a full, clean tree for
        every build.

        This is exactly what we want for official release builds, so that the
        builder can refresh its entire tree based on a new buildspec (which
        might point to a completely different branch or an older revision than
        the last build on the machine).
    """
    if env is None:
      env = {}
    env['DEPOT_TOOLS_UPDATE'] = '0'
    if timeout is None:
      # svn timeout is 2 min; we allow 5
      timeout = 60*5
    self._factory.addStep(chromium_step.GClient,
                          gclient_spec=gclient_spec,
                          gclient_deps=gclient_deps,
                          gclient_nohooks=gclient_nohooks,
                          workdir=self.working_dir,
                          mode='clobber',
                          env=env,
                          timeout=timeout,
                          rm_timeout=60*60) # We don't care how long it takes.

  def AddTaskkillStep(self):
    """Adds a step to kill the running processes before a build."""
    # Use ReturnCodeCommand so we can indicate a "warning" status (orange).
    self._factory.addStep(retcode_command.ReturnCodeCommand,
                          description='taskkill',
                          timeout=60,
                          workdir='',  # Doesn't really matter where we are.
                          command=['python', self._kill_tool])


  # Zip / Extract commands.
  def AddZipBuild(self, src_dir=None, include_files=None,
                  halt_on_failure=False):
    cmd = [self._python, self._zip_tool,
           '--target', self._target,
           '--build-dir', self._build_dir]

    if src_dir is not None:
      cmd += ['--src-dir', src_dir]

    if include_files is not None:
      # Convert the include_files array into a quoted, comma-delimited list
      # for passing as a command-line argument.
      include_arg = '"' + ', '.join(include_files) + '"'
      cmd += ['--include-files', include_arg]

    self._factory.addStep(shell.ShellCommand,
                          name='package_build',
                          timeout=600,
                          description='packaging build',
                          descriptionDone='packaged build',
                          haltOnFailure=halt_on_failure,
                          command=cmd)

  def AddExtractBuild(self, build_url, factory_properties=None):
    """Extract a build.

    Assumes the zip file has a directory like src/xcodebuild which
    contains the actual build.
    """
    factory_properties = factory_properties or {}

    cmd = [self._python, self._extract_tool,
           '--build-dir', self._build_dir,
           '--target', self._target,
           '--build-url', build_url]
    cmd = self.AddBuildProperties(cmd)
    cmd = self.AddFactoryProperties(factory_properties, cmd)
    self.AddTestStep(retcode_command.ReturnCodeCommand, 'extract build', cmd,
                     halt_on_failure=True)

  # Build commands.
  def GetBuildCommand(self, clobber, solution, mode, options=None):
    """Returns a command list to call the _compile_tool in the given build_dir,
    optionally clobbering the build (that is, deleting the build directory)
    first.

    if solution contains a ";", the second part is interpreted as the project.
    """
    cmd = [self._python, self._compile_tool]
    if solution:
      split_solution = solution.split(';')
      cmd.extend(['--solution', split_solution[0]])
      if len(split_solution) == 2:
        cmd.extend(['--project', split_solution[1]])
    cmd.extend(['--target', self._target,
                '--build-dir', self._build_dir])
    if mode is not None:
      cmd.extend(['--mode', mode])
    if clobber:
      cmd.append('--clobber')
    else:
      # Below, WithProperties is appended to the cmd and rendered into a string
      # for each specific build at build-time.  When clobber is None, it renders
      # to an empty string.  When clobber is not None, it renders to the string
      # --clobber.  Note: the :+ after clobber controls this behavior and is not
      # a typo.
      cmd.append(WithProperties('%s', 'clobber:+--clobber'))
    if options:
      cmd.extend(options)
    # Using ListProperties will process and discard None and '' values,
    # otherwise posix platforms will fail.
    return ListProperties(cmd)


  def AddCompileStep(self, solution, clobber=False, description='compiling',
                     descriptionDone='compile', timeout=600, mode=None,
                     options=None):
    """Adds a step to the factory to compile the solution.

    Args:
      solution: the solution/sub-project file to build
      clobber: if True, clobber the build (that is, delete the build
          directory) before building
      description: for the waterfall
      descriptionDone: for the waterfall
      timeout: if no output is received in this many seconds, the compile step
          will be killed
      mode: if given, this will be passed as the --mode option to the compile
          command
      options: list of additional options to pass to the compile command
    """
    self._factory.addStep(cl_command.CLCommand,
                          enable_warnings=0,
                          timeout=timeout,
                          description=description,
                          descriptionDone=descriptionDone,
                          command=self.GetBuildCommand(clobber,
                                                       solution,
                                                       mode,
                                                       options))

  def GetPerfStepClass(self, factory_properties, test_name, log_processor_class,
                       command_class=None, **kwargs):
    """Selects the right build step for the specified perf test."""
    factory_properties = factory_properties or {}
    perf_id = factory_properties.get('perf_id')
    show_results = factory_properties.get('show_perf_results')
    report_link = None
    output_dir = None
    perf_name = None

    if show_results and self._target in self.PERF_TEST_MAPPINGS:
      mapping = self.PERF_TEST_MAPPINGS[self._target]
      perf_name = mapping.get(perf_id)
      if not perf_name:
        raise Exception, ('There is no mapping for identifier %s in %s' %
                            (perf_id, self._target))
      report_link = '%s/%s/%s/%s' % (self.PERF_BASE_URL, perf_name, test_name,
                                     self.PERF_REPORT_URL_SUFFIX)
      output_dir = '%s/%s/%s' % (self.PERF_OUTPUT_DIR, perf_name, test_name)

    return CreatePerformanceStepClass(log_processor_class,
               report_link=report_link, output_dir=output_dir,
               factory_properties=factory_properties, perf_name=perf_name,
               test_name=test_name, command_class=command_class)

  # Checks out and builds clang
  def AddUpdateClangStep(self):
    cmd = [self._update_clang_tool]
    self._factory.addStep(shell.ShellCommand,
                          name='update_clang',
                          timeout=600,
                          description='Updating and building clang and plugins',
                          descriptionDone='clang updated',
                          command=cmd)


class CanCancelBuildShellCommand(shell.ShellCommand):
  """Like ShellCommand but can terminate the build.

  On failure (non-zero exit code of a shell command), this command
  will fake a success but terminate the build.  This keeps the tree
  green but otherwise stops all action.
  """
  def evaluateCommand(self, cmd):
    if cmd.rc != 0:
      reason = 'Build has been cancelled without being a failure.'
      self.build.stopBuild(reason)
      self.build.buildFinished(("Stopped Early", reason), SUCCESS)
    return SUCCESS


class WaterfallLoggingShellCommand(shell.ShellCommand):
  """A shell command that can add messages to the main waterfall page.

  Any string on stdio from this shell command with the prefix
  WATERFALL_LOG will be added to the main waterfall page.  To avoid
  pollution these should be limited and important, such as a summary
  number or version.
  """
  def __init__(self, *args, **kwargs):
    self.messages = []
    # Argh... not a new style class?
    # super(WaterfallLoggingShellCommand, self).__init__(self, *args, **kwargs)
    shell.ShellCommand.__init__(self, *args, **kwargs)

  def commandComplete(self, cmd):
    out = cmd.logs['stdio'].getText()
    self.messages = re.findall('WATERFALL_LOG (.*)', out)

  def getText(self, cmd, results):
    return self.describe(True) + self.messages
