# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


class Test(object):
  """
  Base class for tests that can be retried after deapplying a previously
  applied patch.
  """

  @property
  def name(self):  # pragma: no cover
    """Name of the test."""
    raise NotImplementedError()

  def pre_run(self, api, suffix):  # pragma: no cover
    """Steps to execute before running the test."""
    return []

  def run(self, api, suffix):  # pragma: no cover
    """Run the test. suffix is 'with patch' or 'without patch'."""
    raise NotImplementedError()

  def post_run(self, api, suffix):  # pragma: no cover
    """Steps to execute after running the test."""
    return []

  def has_valid_results(self, api, suffix):  # pragma: no cover
    """
    Returns True if results (failures) are valid.

    This makes it possible to distinguish between the case of no failures
    and the test failing to even report its results in machine-readable
    format.
    """
    raise NotImplementedError()

  def failures(self, api, suffix):  # pragma: no cover
    """Return list of failures (list of strings)."""
    raise NotImplementedError()

  def _step_name(self, suffix):
    """Helper to uniformly combine tests's name with a suffix."""
    if not suffix:
      return self.name
    return '%s (%s)' % (self.name, suffix)


class ArchiveBuildStep(Test):
  def __init__(self, gs_bucket, gs_acl=None):
    self.gs_bucket = gs_bucket
    self.gs_acl = gs_acl

  def run(self, api, suffix):
    return api.chromium.archive_build(
        'archive build',
        self.gs_bucket,
        gs_acl=self.gs_acl,
    )

  @staticmethod
  def compile_targets(_):
    return []


class CheckdepsTest(Test):  # pylint: disable=W0232
  name = 'checkdeps'

  @staticmethod
  def compile_targets(_):
    return []

  @staticmethod
  def run(api, suffix):
    return api.chromium.checkdeps(
        suffix, can_fail_build=(not suffix), always_run=True)

  def has_valid_results(self, api, suffix):
    return api.step_history[self._step_name(suffix)].json.output is not None

  def failures(self, api, suffix):
    results = api.step_history[self._step_name(suffix)].json.output
    result_set = set()
    for result in results:
      for violation in result['violations']:
        result_set.add((result['dependee_path'], violation['include_path']))
    return ['%s: %s' % (r[0], r[1]) for r in result_set]


class CheckpermsTest(Test):  # pylint: disable=W0232
  name = 'checkperms'

  @staticmethod
  def compile_targets(_):
    return []

  @staticmethod
  def run(api, suffix):
    return api.chromium.checkperms(
        suffix, can_fail_build=(not suffix), always_run=True)

  def has_valid_results(self, api, suffix):
    return api.step_history[self._step_name(suffix)].json.output is not None

  def failures(self, api, suffix):
    results = api.step_history[self._step_name(suffix)].json.output
    result_set = set()
    for result in results:
      result_set.add((result['rel_path'], result['error']))
    return ['%s: %s' % (r[0], r[1]) for r in result_set]

class ChecklicensesTest(Test):  # pylint: disable=W0232
  name = 'checklicenses'

  @staticmethod
  def compile_targets(_):
    return []

  @staticmethod
  def run(api, suffix):
    return api.chromium.checklicenses(
        suffix, can_fail_build=(not suffix), always_run=True)

  def has_valid_results(self, api, suffix):
    return api.step_history[self._step_name(suffix)].json.output is not None

  def failures(self, api, suffix):
    results = api.step_history[self._step_name(suffix)].json.output
    result_set = set()
    for result in results:
      result_set.add((result['filename'], result['license']))
    return ['%s: %s' % (r[0], r[1]) for r in result_set]


class Deps2GitTest(Test):  # pylint: disable=W0232
  name = 'deps2git'

  @staticmethod
  def compile_targets(_):
    return []

  @staticmethod
  def run(api, suffix):
    yield (
      api.chromium.deps2git(suffix, can_fail_build=(not suffix)),
      api.chromium.deps2submodules()
    )

  def has_valid_results(self, api, suffix):
    return api.step_history[self._step_name(suffix)].json.output is not None

  def failures(self, api, suffix):
    return api.step_history[self._step_name(suffix)].json.output


class GTestTest(Test):
  def __init__(self, name, args=None, compile_targets=None, flakiness_dash=False):
    self._name = name
    self._args = args or []
    self.flakiness_dash = flakiness_dash

  @property
  def name(self):
    return self._name

  def compile_targets(self, api):
    if api.chromium.c.TARGET_PLATFORM == 'android':
      return [self.name + '_apk']

    # On iOS we rely on 'All' target being compiled instead of using
    # individual targets.
    if api.chromium.c.TARGET_PLATFORM == 'ios':
      return []

    return [self.name]

  def run(self, api, suffix):
    if api.chromium.c.TARGET_PLATFORM == 'android':
      return api.chromium_android.run_test_suite(self.name, self._args)

    def followup_fn(step_result):
      r = step_result.json.gtest_results
      p = step_result.presentation

      if r.valid:
        p.step_text += api.test_utils.format_step_text([
            ['failures:', r.failures]
        ])

    # Copy the list because run can be invoked multiple times and we modify
    # the local copy.
    args = self._args[:]

    if suffix == 'without patch':
      args.append(api.chromium.test_launcher_filter(
                      self.failures(api, 'with patch')))

    kwargs = {}
    if suffix:
      # TODO(phajdan.jr): Just remove it, keeping for now to avoid
      # expectation changes.
      kwargs['parallel'] = True

      # TODO(phajdan.jr): Always do that, keeping for now to avoid
      # expectation changes.
      kwargs['test_launcher_summary_output'] = api.json.gtest_results(
          add_json_log=False)
      kwargs['followup_fn'] = followup_fn
    else:
      # TODO(phajdan.jr): Always do that, keeping for now to avoid
      # expectation changes.
      kwargs['test_type'] = self.name

    return api.chromium.runtest(
        self.name,
        args,
        annotate='gtest',
        xvfb=True,
        name=self._step_name(suffix),
        can_fail_build=False,
        flakiness_dash=self.flakiness_dash,
        step_test_data=lambda: api.json.test_api.canned_gtest_output(True),
        **kwargs)

  def has_valid_results(self, api, suffix):
    step_name = self._step_name(suffix)
    gtest_results = api.step_history[step_name].json.gtest_results
    if not gtest_results.valid:  # pragma: no cover
      return False
    global_tags = gtest_results.raw.get('global_tags', [])
    return 'UNRELIABLE_RESULTS' not in global_tags

  def failures(self, api, suffix):
    step_name = self._step_name(suffix)
    return api.step_history[step_name].json.gtest_results.failures


class DynamicGTestTests(Test):
  def __init__(self, buildername, flakiness_dash=True):
    self.buildername = buildername
    self.flakiness_dash = flakiness_dash

  @staticmethod
  def _canonicalize_test(test):
    if isinstance(test, basestring):
      return {'test': test, 'shard_index': 0, 'total_shards': 1}
    return test

  def _get_test_spec(self, api):
    all_test_specs = api.step_history['read test spec'].json.output
    return all_test_specs.get(self.buildername, {})

  def _get_tests(self, api):
    return [self._canonicalize_test(t) for t in
            self._get_test_spec(api).get('gtest_tests', [])]

  def run(self, api, suffix):
    steps = []
    for test in self._get_tests(api):
      args = []
      if test['shard_index'] != 0 or test['total_shards'] != 1:
        args.extend(['--test-launcher-shard-index=%d' % test['shard_index'],
                     '--test-launcher-total-shards=%d' % test['total_shards']])
      steps.append(api.chromium.runtest(
          test['test'], test_type=test['test'], args=args, annotate='gtest',
          xvfb=True, flakiness_dash=self.flakiness_dash))

    return steps

  def compile_targets(self, api):
    explicit_targets = self._get_test_spec(api).get('compile_targets', [])
    test_targets = [t['test'] for t in self._get_tests(api)]
    # Remove duplicates.
    return sorted(set(explicit_targets + test_targets))


class SwarmingGTestTest(Test):
  def __init__(self, name, args=None, shards=1):
    self._name = name
    self._args = args or []
    self._shards = shards
    self._tasks = {}
    self._results = {}

  @property
  def name(self):
    return self._name

  def compile_targets(self, _):
    # <X>_run target depends on <X>, and then isolates it invoking isolate.py.
    # It is a convention, not a hard coded rule.
    return [self._name + '_run']

  def pre_run(self, api, suffix):
    """Launches the test on Swarming."""
    assert suffix not in self._tasks, (
        'Test %s was already triggered' % self._step_name(suffix))

    # *.isolated may be missing if *_run target is misconfigured. It's a error
    # in gyp, not a recipe failure. So carry on with recipe execution.
    isolated_hash = api.isolate.isolated_tests.get(self._name)
    if not isolated_hash:
      return api.python.inline(
          '[error] %s' % self._step_name(suffix),
          r"""
          import sys
          print '*.isolated file for target %s is missing' % sys.argv[1]
          sys.exit(1)
          """,
          args=[self._name],
          always_run=True)

    # If rerunning without a patch, run only tests that failed.
    args = self._args[:]
    if suffix == 'without patch':
      failed_tests = sorted(self.failures(api, 'with patch'))
      args.append('--gtest_filter=%s' % ':'.join(failed_tests))

    # Trigger the test on swarming.
    self._tasks[suffix] = api.swarming.gtest_task(
        title=self._step_name(suffix),
        isolated_hash=isolated_hash,
        shards=self._shards,
        test_launcher_summary_output=api.json.gtest_results(
            add_json_log=False),
        extra_args=args)
    return api.swarming.trigger([self._tasks[suffix]], always_run=True)

  def run(self, api, suffix):  # pylint: disable=R0201
    """Not used. All logic in pre_run, post_run."""
    return []

  def post_run(self, api, suffix):
    """Waits for launched test to finish and collect the results."""
    assert suffix not in self._results, (
        'Results of %s were already collected' % self._step_name(suffix))

    # Emit error if test wasn't triggered. This happens if *.isolated is not
    # found. (The build is already red by this moment anyway).
    if suffix not in self._tasks:
      return api.python.inline(
          '[collect error] %s' % self._step_name(suffix),
          r"""
          import sys
          print '%s wasn\'t triggered' % sys.argv[1]
          sys.exit(1)
          """,
          args=[self._name],
          always_run=True)

    # Update step presentation, store step results in self._results.
    def followup_fn(step_result):
      r = step_result.json.gtest_results
      p = step_result.presentation
      if r.valid:
        p.step_text += api.test_utils.format_step_text([
            ['failures:', r.failures]
        ])
      self._results[suffix] = r

    # Wait for test on swarming to finish. If swarming infrastructure is
    # having issues, this step produces no valid *.json test summary, and
    # 'has_valid_results' returns False.
    return api.swarming.collect(
        [self._tasks[suffix]],
        always_run=True,
        can_fail_build=(not suffix),
        followup_fn=followup_fn)

  def has_valid_results(self, api, suffix):
    # Test wasn't triggered or wasn't collected.
    if suffix not in self._tasks or not suffix in self._results:
      return False
    # Test ran, but failed to produce valid *.json.
    gtest_results = self._results[suffix]
    if not gtest_results.valid:  # pragma: no cover
      return False
    global_tags = gtest_results.raw.get('global_tags', [])
    return 'UNRELIABLE_RESULTS' not in global_tags

  def failures(self, api, suffix):
    assert self.has_valid_results(api, suffix)
    return self._results[suffix].failures


class TelemetryUnitTests(Test):
  @staticmethod
  def run(api, suffix):
    return api.chromium.run_telemetry_unittests()

  @staticmethod
  def compile_targets(_):
    return ['chrome']

class TelemetryPerfUnitTests(Test):
  @staticmethod
  def run(api, suffix):
    return api.chromium.run_telemetry_perf_unittests()

  @staticmethod
  def compile_targets(_):
    return ['chrome']


class NaclIntegrationTest(Test):  # pylint: disable=W0232
  name = 'nacl_integration'

  @staticmethod
  def compile_targets(_):
    return ['chrome']

  def run(self, api, suffix):
    args = [
    ]

    if suffix:
      # TODO(phajdan.jr): Always do that, keeping for now to avoid
      # expectation changes.
      args.extend([
        '--mode', api.chromium.c.build_config_fs,
        '--json_build_results_output_file', api.json.output(),
      ])
    else:
      # TODO(phajdan.jr): Just remove it, keeping for now to avoid
      # expectation changes.
      args.extend([
        '--mode', api.chromium.c.BUILD_CONFIG,
      ])

    return api.python(
        self._step_name(suffix),
        api.path['checkout'].join('chrome',
                          'test',
                          'nacl_test_injection',
                          'buildbot_nacl_integration.py'),
        args,
        can_fail_build=(not suffix),
        step_test_data=lambda: api.m.json.test_api.output([]))

  def has_valid_results(self, api, suffix):
    return api.step_history[self._step_name(suffix)].json.output is not None

  def failures(self, api, suffix):
    failures = api.step_history[self._step_name(suffix)].json.output
    return [f['raw_name'] for f in failures]


class AndroidInstrumentationTest(Test):
  def __init__(self, name, compile_target, test_data=None,
               adb_install_apk=None):
    self._name = name
    self.compile_target = compile_target

    self.test_data = test_data
    self.adb_install_apk = adb_install_apk

  @property
  def name(self):
    return self._name

  def run(self, api, suffix):
    assert api.chromium.c.TARGET_PLATFORM == 'android'
    if self.adb_install_apk:
      yield api.chromium_android.adb_install_apk(
          self.adb_install_apk[0], self.adb_install_apk[1])
    yield api.chromium_android.run_instrumentation_suite(
        self.name, test_data=self.test_data,
        flakiness_dashboard='test-results.appspot.com',
        verbose=True)

  def compile_targets(self, _):
    return [self.compile_target]


class MojoPythonTests(Test):  # pylint: disable=W0232
  name = 'mojo_python_tests'

  @staticmethod
  def compile_targets(_):
    return []

  def run(self, api, suffix):
    args = ['--write-full-results-to',
            api.json.test_results(add_json_log=False)]
    if suffix == 'without patch':
      args.extend(self.failures(api, 'with patch'))

    def followup_fn(step_result):
      r = step_result.json.test_results
      p = step_result.presentation

      p.step_text += api.test_utils.format_step_text([
        ['unexpected_failures:', r.unexpected_failures.keys()],
      ])

    return api.python(
        self._step_name(suffix),
        api.path['checkout'].join(
            'mojo',
            'tools',
            'run_mojo_python_tests.py'),
        args,
        can_fail_build=(not suffix),
        step_test_data=lambda: api.json.test_api.canned_test_output(
            True), followup_fn=followup_fn)

  def has_valid_results(self, api, suffix):
    # TODO(dpranke): we should just return zero/nonzero for success/fail.
    # crbug.com/357866
    step = api.step_history[self._step_name(suffix)]
    return (step.json.test_results.valid and
            step.retcode <= step.json.test_results.MAX_FAILURES_EXIT_STATUS)

  def failures(self, api, suffix):
    sn = self._step_name(suffix)
    return api.step_history[sn].json.test_results.unexpected_failures


class BlinkTest(Test):
  name = 'webkit_tests'

  def __init__(self, api):
    self.results_dir = api.path['slave_build'].join('layout-test-results')
    self.layout_test_wrapper = api.path['build'].join(
        'scripts', 'slave', 'chromium', 'layout_test_wrapper.py')

  def run(self, api, suffix):
    args = ['--target', api.chromium.c.BUILD_CONFIG,
            '-o', self.results_dir,
            '--build-dir', api.chromium.c.build_dir,
            '--json-test-results', api.json.test_results(add_json_log=False)]
    if suffix == 'without patch':
      test_list = "\n".join(self.failures(api, 'with patch'))
      args.extend(['--test-list', api.raw_io.input(test_list),
                   '--skipped', 'always'])

    if 'oilpan' in api.properties['buildername']:
      args.extend(['--additional-expectations',
                   api.path['checkout'].join('third_party', 'WebKit',
                                             'LayoutTests',
                                             'OilpanExpectations')])

    def followup_fn(step_result):
      r = step_result.json.test_results
      p = step_result.presentation

      p.step_text += api.test_utils.format_step_text([
        ['unexpected_flakes:', r.unexpected_flakes.keys()],
        ['unexpected_failures:', r.unexpected_failures.keys()],
        ['Total executed: %s' % r.num_passes],
      ])

      if r.unexpected_flakes or r.unexpected_failures:
        p.status = 'WARNING'
      else:
        p.status = 'SUCCESS'

    yield api.chromium.runtest(self.layout_test_wrapper,
                               args,
                               name=self._step_name(suffix),
                               can_fail_build=False,
                               followup_fn=followup_fn)

    if suffix == 'with patch':
      buildername = api.properties['buildername']
      buildnumber = api.properties['buildnumber']
      def archive_webkit_tests_results_followup(step_result):
        base = (
          "https://storage.googleapis.com/chromium-layout-test-archives/%s/%s"
          % (buildername, buildnumber))

        step_result.presentation.links['layout_test_results'] = (
            base + '/layout-test-results/results.html')
        step_result.presentation.links['(zip)'] = (
            base + '/layout-test-results.zip')

      archive_layout_test_results = api.path['build'].join(
          'scripts', 'slave', 'chromium', 'archive_layout_test_results.py')

      yield api.python(
        'archive_webkit_tests_results',
        archive_layout_test_results,
        [
          '--results-dir', self.results_dir,
          '--build-dir', api.chromium.c.build_dir,
          '--build-number', buildnumber,
          '--builder-name', buildername,
          '--gs-bucket', 'gs://chromium-layout-test-archives',
        ] + api.json.property_args(),
        followup_fn=archive_webkit_tests_results_followup
      )

  def has_valid_results(self, api, suffix):
    step = api.step_history[self._step_name(suffix)]
    # TODO(dpranke): crbug.com/357866 - note that all comparing against
    # MAX_FAILURES_EXIT_STATUS tells us is that we did not exit early
    # or abnormally; it does not tell us how many failures there actually
    # were, which might be much higher (up to 5000 diffs, where we
    # would bail out early with --exit-after-n-failures) or lower
    # if we bailed out after 100 crashes w/ -exit-after-n-crashes, in
    # which case the retcode is actually 130
    return (step.json.test_results.valid and
            step.retcode <= step.json.test_results.MAX_FAILURES_EXIT_STATUS)

  def failures(self, api, suffix):
    sn = self._step_name(suffix)
    return api.step_history[sn].json.test_results.unexpected_failures


IOS_TESTS = [
  GTestTest('base_unittests'),
  GTestTest('components_unittests'),
  GTestTest('crypto_unittests'),
  GTestTest('gfx_unittests'),
  GTestTest('url_unittests'),
  GTestTest('content_unittests'),
  GTestTest('net_unittests'),
  GTestTest('ui_unittests'),
  GTestTest('sync_unit_tests'),
  GTestTest('sql_unittests'),
]
