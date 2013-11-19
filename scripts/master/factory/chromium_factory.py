# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Utility class to build the chromium master BuildFactory's.

Based on gclient_factory.py and adds chromium-specific steps."""

import re

from master.factory import chromium_commands
from master.factory import gclient_factory

import config


def ForceComponent(target, project, gclient_env):
  # Force all bots to specify the "Component" gyp variables, unless it is
  # already set.
  gyp_defines = gclient_env.setdefault('GYP_DEFINES', '')
  if ('component=' not in gyp_defines and
      # build_for_tool=drmemory wants the component build (crbug.com/137180).
      'build_for_tool=memcheck' not in gyp_defines and
      'build_for_tool=tsan' not in gyp_defines):
    if target == 'Debug':
      component = 'shared_library'
    else:
      component = 'static_library'
    gclient_env['GYP_DEFINES'] = gyp_defines + ' component=' + component


def FixForGomaWin(options, target, gclient_env):
  """Fix gyp variables required for goma on Windows,
  unless it is already set.

  Args:
    options: a list of string for factory options.
    target: a string of build target (e.g. Debug, Release).
    gclient_env: a dict for gclient_env.
  """
  options = options or {}
  if (not '--compiler=goma' in options and
      not '--compiler=goma-clang' in options):
    return
  gyp_defines = gclient_env.get('GYP_DEFINES', '')
  # goma couldn't work with pdbserv.
  if 'fastbuild=1' not in gyp_defines and 'win_z7=1' not in gyp_defines:
    if target.startswith('Debug'):
      gyp_defines += ' win_z7=1'
    else:
      gyp_defines += ' fastbuild=1'
  # goma couldn't handle precompiled headers.
  if 'chromium_win_pch=0' not in gyp_defines:
    gyp_defines += ' chromium_win_pch=0'
  gclient_env['GYP_DEFINES'] = gyp_defines


class ChromiumFactory(gclient_factory.GClientFactory):
  """Encapsulates data and methods common to the chromium master.cfg files."""

  DEFAULT_TARGET_PLATFORM = config.Master.default_platform

  MEMORY_TOOLS_GYP_DEFINES = 'build_for_tool=memcheck'

  # gclient custom vars
  CUSTOM_VARS_GOOGLECODE_URL = ('googlecode_url', config.Master.googlecode_url)
  CUSTOM_VARS_SOURCEFORGE_URL = ('sourceforge_url',
                                 config.Master.sourceforge_url)
  CUSTOM_VARS_WEBKIT_MIRROR = ('webkit_trunk', config.Master.webkit_trunk_url)
  CUSTOM_VARS_NACL_TRUNK_URL = ('nacl_trunk', config.Master.nacl_trunk_url)
  # safe sync urls
  SAFESYNC_URL_CHROMIUM = 'http://chromium-status.appspot.com/lkgr'

  # gclient additional custom deps
  CUSTOM_DEPS_V8_LATEST = ('src/v8',
    'http://v8.googlecode.com/svn/branches/bleeding_edge')
  CUSTOM_DEPS_V8_TRUNK = ('src/v8',
    'http://v8.googlecode.com/svn/trunk')
  CUSTOM_DEPS_WEBRTC_TRUNK = ('src/third_party/webrtc',
    config.Master.webrtc_url + '/trunk/webrtc@$$WEBRTC_REV$$')
  CUSTOM_DEPS_LIBJINGLE_TRUNK = ('src/third_party/libjingle/source/talk',
    config.Master.webrtc_url + '/trunk/talk@$$WEBRTC_REV$$')
  CUSTOM_DEPS_AVPERF = ('src/chrome/test/data/media/avperf',
    config.Master.trunk_url + '/deps/avperf')
  CUSTOM_VARS_NACL_LATEST = [
    ('nacl_revision', '$$NACL_REV$$'),
  ]
  CUSTOM_DEPS_VALGRIND = ('src/third_party/valgrind',
     config.Master.trunk_url + '/deps/third_party/valgrind/binaries')
  CUSTOM_DEPS_DEVTOOLS_PERF = [
    ('src/third_party/WebKit/PerformanceTests',
     config.Master.webkit_trunk_url + '/PerformanceTests'),
    ('src/third_party/WebKit/LayoutTests/http/tests/inspector',
     config.Master.webkit_trunk_url + '/LayoutTests/http/tests/inspector'),
    ('src/third_party/WebKit/LayoutTests/inspector',
     config.Master.webkit_trunk_url + '/LayoutTests/inspector'),
  ]
  CUSTOM_DEPS_TSAN_WIN = ('src/third_party/tsan',
     config.Master.trunk_url + '/deps/third_party/tsan')
  CUSTOM_DEPS_NACL_VALGRIND = ('src/third_party/valgrind/bin',
     config.Master.nacl_trunk_url + '/src/third_party/valgrind/bin')
  CUSTOM_DEPS_WEBDRIVER_JAVA_TESTS = (
     'src/chrome/test/chromedriver/third_party/java_tests',
     config.Master.trunk_url + '/deps/third_party/webdriver')

  CUSTOM_DEPS_GYP = [
    ('src/tools/gyp', 'http://gyp.googlecode.com/svn/trunk')]
  CUSTOM_DEPS_GIT_INTERNAL = [
      ('src/third_party/adobe/flash/symbols/ppapi/mac', None),
      ('src/third_party/adobe/flash/symbols/ppapi/mac_64', None),
      ('src/third_party/adobe/flash/symbols/ppapi/linux', None),
      ('src/third_party/adobe/flash/symbols/ppapi/linux_x64', None),
      ('src/third_party/adobe/flash/symbols/ppapi/win', None),
      ('src/third_party/adobe/flash/symbols/ppapi/win_x64', None),
  ]

  # A map used to skip dependencies when a test is not run.
  # The map key is the test name. The map value is an array containing the
  # dependencies that are not needed when this test is not run.
  NEEDED_COMPONENTS = {
    '^(webkit)$':
      [('src/webkit/data/layout_tests/LayoutTests', None),
       ('src/third_party/WebKit/LayoutTests', None),],
  }

  NEEDED_COMPONENTS_INTERNAL = {
    'memory':
      [('src/data/memory_test', None)],
    'page_cycler':
      [('src/data/page_cycler', None)],
    '(selenium|chrome_frame)':
      [('src/data/selenium_core', None)],
    'browser_tests':
      [('src/chrome/test/data/firefox2_profile/searchplugins', None),
       ('src/chrome/test/data/firefox2_searchplugins', None),
       ('src/chrome/test/data/firefox3_profile/searchplugins', None),
       ('src/chrome/test/data/firefox3_searchplugins', None),
       ('src/chrome/test/data/ssl/certs', None)],
    'unit':
      [('src/chrome/test/data/osdd', None)],
    '^(webkit|content_unittests)$':
      [('src/webkit/data/bmp_decoder', None),
       ('src/webkit/data/ico_decoder', None),
       ('src/webkit/data/test_shell/plugins', None),
       ('src/webkit/data/xbm_decoder', None)],
    'mach_ports':
      [('src/data/mach_ports', None)],
    # Unused stuff:
    'autodiscovery':
      [('src/data/autodiscovery', None)],
    'esctf':
      [('src/data/esctf', None)],
    'grit':
      [('src/tools/grit/grit/test/data', None)],
    'mozilla_js':
      [('src/data/mozilla_js_tests', None)],
  }

  # List of test groups for media tests.  Media tests generate a lot of data, so
  # it's nice to separate them into different graphs.  Each tuple corresponds to
  # a PyAuto test suite name and indicates if the suite contains perf tests.
  MEDIA_TEST_GROUPS = [
      ('AV_PERF', True),
  ]

  # Minimal deps for running PyAuto.
  # http://dev.chromium.org/developers/pyauto
  PYAUTO_DEPS = \
      [('src/chrome/test/data',
        config.Master.trunk_url + '/src/chrome/test/data'),
       ('src/chrome/test/pyautolib',
        config.Master.trunk_url + '/src/chrome/test/pyautolib'),
       ('src/chrome/test/functional',
        config.Master.trunk_url + '/src/chrome/test/functional'),
       ('src/content/test/data',
        config.Master.trunk_url + '/src/content/test/data'),
       ('src/third_party/simplejson',
        config.Master.trunk_url + '/src/third_party/simplejson'),
       ('src/net/data/ssl/certificates',
        config.Master.trunk_url + '/src/net/data/ssl/certificates'),
       ('src/net/tools/testserver',
        config.Master.trunk_url + '/src/net/tools/testserver'),
       # It would be better to use config.Master.googlecode_url here.
       # But it causes QA buildbot failures on Mac beta and stable.
       # See http://crbug.com/155918#c21 .
       ('src/third_party/pyftpdlib/src',
        'http://pyftpdlib.googlecode.com/svn/trunk'),
       ('src/third_party/pywebsocket/src',
        'http://pywebsocket.googlecode.com/svn/trunk/src'),
       ('src/third_party/tlslite',
        config.Master.trunk_url + '/src/third_party/tlslite'),
       ('src/third_party/python_26',
        config.Master.trunk_url + '/tools/third_party/python_26'),
       ('src/chrome/test/data/media/avperf',
        config.Master.trunk_url + '/deps/avperf'),
       ('webdriver.DEPS',
        config.Master.trunk_url + '/src/chrome/test/pyautolib/' +
            'webdriver.DEPS'),
        ]
  # Extend if we can.
  # pylint: disable=E1101
  if config.Master.trunk_internal_url:
    PYAUTO_DEPS.append(('src/content/test/data/plugin',
                        config.Master.trunk_internal_url +
                        '/data/chrome_plugin_tests'))
    PYAUTO_DEPS.append(('src/chrome/test/data/pyauto_private',
                        config.Master.trunk_internal_url +
                        '/data/pyauto_private'))
    PYAUTO_DEPS.append(('src/data/page_cycler',
                        config.Master.trunk_internal_url +
                        '/data/page_cycler'))
    CUSTOM_DEPS_DEVTOOLS_PERF.append(('src/data/devtools_test_pages',
                                      config.Master.trunk_internal_url +
                                      '/data/devtools_test_pages'))

  def __init__(self, build_dir, target_platform=None, pull_internal=True,
               full_checkout=False, additional_svn_urls=None, name=None,
               custom_deps_list=None, nohooks_on_update=False, target_os=None,
               swarm_client_canary=False):
    if full_checkout:
      needed_components = None
    else:
      needed_components = self.NEEDED_COMPONENTS
    main = gclient_factory.GClientSolution(config.Master.trunk_url_src,
               needed_components=needed_components,
               name=name,
               custom_deps_list=custom_deps_list,
               custom_vars_list=[self.CUSTOM_VARS_WEBKIT_MIRROR,
                                 self.CUSTOM_VARS_GOOGLECODE_URL,
                                 self.CUSTOM_VARS_SOURCEFORGE_URL,
                                 self.CUSTOM_VARS_NACL_TRUNK_URL])
    internal_custom_deps_list = [main]
    if config.Master.trunk_internal_url_src and pull_internal:
      if full_checkout:
        needed_components = None
      else:
        needed_components = self.NEEDED_COMPONENTS_INTERNAL
      internal = gclient_factory.GClientSolution(
                     config.Master.trunk_internal_url_src,
                     needed_components=needed_components)
      internal_custom_deps_list.append(internal)

    additional_svn_urls = additional_svn_urls or []
    for svn_url in additional_svn_urls:
      solution = gclient_factory.GClientSolution(svn_url)
      internal_custom_deps_list.append(solution)

    gclient_factory.GClientFactory.__init__(self, build_dir,
                                            internal_custom_deps_list,
                                            target_platform=target_platform,
                                            nohooks_on_update=nohooks_on_update,
                                            target_os=target_os)
    if swarm_client_canary:
      # Contrary to other canaries like blink, v8, we don't really care about
      # having one build per swarm_client commits by having an additional source
      # change listener so just fetching @ToT all the time is good enough.
      self._solutions[0].custom_vars_list.append(('swarm_revision', ''))

  def _AddTests(self, factory_cmd_obj, tests, mode=None,
                factory_properties=None):
    """Add the tests listed in 'tests' to the factory_cmd_obj."""
    factory_properties = factory_properties or {}
    tests = (tests or [])[:]

    # This function is too crowded, try to simplify it a little.
    def R(*testnames):
      for test in testnames:
        if gclient_factory.ShouldRunTest(tests, test):
          tests.remove(test)
          return True
    f = factory_cmd_obj
    fp = factory_properties

    # Copy perf expectations from slave to master for use later.
    if factory_properties.get('expectations'):
      f.AddUploadPerfExpectations(factory_properties)

    # When modifying the order of the tests here, please take
    # http://build.chromium.org/buildbot/waterfall/stats into account.
    # Tests that fail more often should be earlier in the queue.

    # Check for goma
    if R('diagnose_goma'):
      f.AddDiagnoseGomaStep()

    # Run interactive_ui_tests first to make sure it does not fail if another
    # test running before it leaks a window or a popup (crash dialog, etc).
    if R('interactive_ui_tests'):
      f.AddGTestTestStep('interactive_ui_tests', fp)
    if R('interactive_ui_tests_br'):
      f.AddBuildrunnerGTest('interactive_ui_tests', fp)

    # interactive_ui_tests specifically for Instant Extended.
    if R('instant_extended_manual_tests'):
      arg_list = [
          '--gtest_filter=InstantExtendedManualTest.*',
          '--run-manual',
          '--enable-benchmarking',
          '--enable-stats-table',
          '--ignore-certificate-errors',
      ]
      f.AddBuildrunnerGTest('interactive_ui_tests', factory_properties=fp,
                            arg_list=arg_list)

    # Check for an early bail.  Do early since this may cancel other tests.
    if R('check_lkgr'):
      f.AddCheckLKGRStep()

    # Scripted checks to verify various properties of the codebase:
    if R('check_deps2git'):
      f.AddDeps2GitStep()
    if R('check_deps2git_br'):
      f.AddBuildrunnerDeps2GitStep()
    if R('check_deps'):
      f.AddCheckDepsStep()
    if R('check_deps_br'):
      f.AddBuildrunnerCheckDepsStep()
    if R('check_bins'):
      f.AddCheckBinsStep()
    if R('check_bins_br'):
      f.AddBuildrunnerCheckBinsStep()
    if R('check_perms'):
      f.AddCheckPermsStep()
    if R('check_perms_br'):
      f.AddBuildrunnerCheckPermsStep()
    if R('check_licenses'):
      f.AddCheckLicensesStep(fp)
    if R('check_licenses_br'):
      f.AddBuildrunnerCheckLicensesStep(fp)

    # Small ("module") unit tests:
    if R('base_unittests'):
      f.AddGTestTestStep('base_unittests', fp)
    if R('base_unittests_br'):
      f.AddBuildrunnerGTest('base_unittests', fp)
    if R('cacheinvalidation_unittests'):
      f.AddGTestTestStep('cacheinvalidation_unittests', fp)
    if R('cacheinvalidation_br'):
      f.AddBuildrunnerGTest('cacheinvalidation_unittests', fp)
    if R('cc_unittests'):
      f.AddGTestTestStep('cc_unittests', fp)
    if R('cc_unittests_br'):
      f.AddBuildrunnerGTest('cc_unittests', fp)
    if R('chromedriver2_unittests'):
      f.AddGTestTestStep('chromedriver2_unittests', fp)
    if R('chromedriver2_unittests_br'):
      f.AddBuildrunnerGTest('chromedriver2_unittests', fp)
    if R('chromeos_unittests'):
      f.AddGTestTestStep('chromeos_unittests', fp)
    if R('chromeos_unittests_br'):
      f.AddBuildrunnerGTest('chromeos_unittests', fp)
    if R('components_unittests'):
      f.AddGTestTestStep('components_unittests', fp)
    if R('components_unittests_br'):
      f.AddBuildrunnerGTest('components_unittests', fp)
    if R('courgette_unittests'):
      f.AddGTestTestStep('courgette_unittests', fp)
    if R('courgette_br'):
      f.AddBuildrunnerGTest('courgette_unittests', fp)
    if R('crypto_unittests'):
      f.AddGTestTestStep('crypto_unittests', fp)
    if R('crypto_br'):
      f.AddBuildrunnerGTest('crypto_unittests', fp)
    if R('dbus'):
      f.AddGTestTestStep('dbus_unittests', fp)
    if R('dbus_br'):
      f.AddBuildrunnerGTest('dbus_unittests', fp)
    if R('google_apis_unittests'):
      f.AddGTestTestStep('google_apis_unittests', fp)
    if R('google_apis_unittests_br'):
      f.AddBuildrunnerGTest('google_apis_unittests', fp)
    if R('gpu', 'gpu_unittests'):
      f.AddGTestTestStep(
          'gpu_unittests', fp, arg_list=['--gmock_verbose=error'])
    if R('gpu_br'):
      f.AddBuildrunnerGTest(
          'gpu_unittests', fp, arg_list=['--gmock_verbose=error'])
    if R('googleurl_unittests'):
      f.AddGTestTestStep('googleurl_unittests', fp)
    if R('googleurl', 'url_unittests'):
      f.AddGTestTestStep('url_unittests', fp)
    if R('googleurl_br'):
      f.AddBuildrunnerGTest('url_unittests', fp)
    if R('jingle', 'jingle_unittests'):
      f.AddGTestTestStep('jingle_unittests', fp)
    if R('jingle_br'):
      f.AddBuildrunnerGTest('jingle_unittests', fp)
    if R('content_unittests'):
      f.AddGTestTestStep('content_unittests', fp)
    if R('content_unittests_br'):
      f.AddBuildrunnerGTest('content_unittests', fp)
    if R('keyboard_unittests'):
      f.AddBuildrunnerGTest('keyboard_unittests', fp)
    if R('device_unittests'):
      f.AddGTestTestStep('device_unittests', fp)
    if R('device_unittests_br'):
      f.AddBuildrunnerGTest('device_unittests', fp)
    if R('media', 'media_unittests'):
      f.AddGTestTestStep('media_unittests', fp)
    if R('media_br'):
      f.AddBuildrunnerGTest('media_unittests', fp)
    if R('net', 'net_unittests'):
      f.AddGTestTestStep('net_unittests', fp)
    if R('net_br'):
      f.AddBuildrunnerGTest('net_unittests', fp)
    if R('ppapi_unittests'):
      f.AddGTestTestStep('ppapi_unittests', fp)
    if R('ppapi_unittests_br'):
      f.AddBuildrunnerGTest('ppapi_unittests', fp)
    if R('printing', 'printing_unittests'):
      f.AddGTestTestStep('printing_unittests', fp)
    if R('printing_br'):
      f.AddBuildrunnerGTest('printing_unittests', fp)
    if R('remoting', 'remoting_unittests'):
      f.AddGTestTestStep('remoting_unittests', fp)
    if R('remoting_br'):
      f.AddBuildrunnerGTest('remoting_unittests', fp)
    # Windows sandbox
    if R('sbox_unittests'):
      f.AddGTestTestStep('sbox_unittests', fp)
    if R('sbox_unittests_br'):
      f.AddBuildrunnerGTest('sbox_unittests', fp)
    if R('sbox_integration_tests'):
      f.AddGTestTestStep('sbox_integration_tests', fp)
    if R('sbox_integration_tests_br'):
      f.AddBuildrunnerGTest('sbox_integration_tests', fp)
    if R('sbox_validation_tests'):
      f.AddBuildrunnerGTest('sbox_validation_tests', fp)
    if R('sbox_validation_tests_br'):
      f.AddBuildrunnerGTest('sbox_validation_tests', fp)
    if R('sandbox'):
      f.AddGTestTestStep('sbox_unittests', fp)
      f.AddGTestTestStep('sbox_integration_tests', fp)
      f.AddGTestTestStep('sbox_validation_tests', fp)
    if R('sandbox_br'):
      f.AddBuildrunnerGTest('sbox_unittests', fp)
      f.AddBuildrunnerGTest('sbox_integration_tests', fp)
      f.AddBuildrunnerGTest('sbox_validation_tests', fp)
    # Linux sandbox
    if R('sandbox_linux_unittests'):
      f.AddGTestTestStep('sandbox_linux_unittests', fp)
    if R('sandbox_linux_unittests_br'):
      f.AddBuildrunnerGTest('sandbox_linux_unittests', fp)
    if R('telemetry_unittests'):
      f.AddTelemetryUnitTests()
    if R('telemetry_unittests_br'):
      f.AddBuildrunnerTelemetryUnitTests()
    if R('telemetry_perf_unittests'):
      f.AddTelemetryPerfUnitTests()
    if R('telemetry_perf_unittests_br'):
      f.AddBuildrunnerTelemetryPerfUnitTests()
    if R('ui_unittests'):
      f.AddGTestTestStep('ui_unittests', fp)
    if R('ui_unittests_br'):
      f.AddBuildrunnerGTest('ui_unittests', fp)
    if R('views', 'views_unittests'):
      f.AddGTestTestStep('views_unittests', fp)
    if R('views_br'):
      f.AddBuildrunnerGTest('views_unittests', fp)
    if R('aura'):
      f.AddGTestTestStep('aura_unittests', fp)
    if R('aura_br'):
      f.AddBuildrunnerGTest('aura_unittests', fp)
    if R('aura_shell') or R('ash') or R('ash_unittests'):
      f.AddGTestTestStep('ash_unittests', fp)
    if R('aura_shell_br', 'ash_br', 'ash_unittests_br'):
      f.AddBuildrunnerGTest('ash_unittests', fp)
    if R('app_list_unittests'):
      f.AddGTestTestStep('app_list_unittests', fp)
    if R('app_list_unittests_br'):
      f.AddBuildrunnerGTest('app_list_unittests', fp)
    if R('message_center_unittests'):
      f.AddGTestTestStep('message_center_unittests', fp)
    if R('message_center_unittests_br'):
      f.AddBuildrunnerGTest('message_center_unittests', fp)
    if R('compositor'):
      f.AddGTestTestStep('compositor_unittests', fp)
    if R('compositor_br'):
      f.AddBuildrunnerGTest('compositor_unittests', fp)
    if R('events'):
      f.AddGTestTestStep('events_unittests', fp)
    if R('events_br'):
      f.AddBuildrunnerGTest('events_unittests', fp)

    # Medium-sized tests (unit and browser):
    if R('unit'):
      f.AddChromeUnitTests(fp)
    if R('unit_br'):
      f.AddBuildrunnerChromeUnitTests(fp)
    # A snapshot of the "ChromeUnitTests" available for individual selection
    if R('ipc_tests'):
      f.AddGTestTestStep('ipc_tests', fp)
    if R('ipc_tests_br'):
      f.AddBuildrunnerGTest('ipc_tests', fp)
    if R('unit_sync', 'sync_unit_tests'):
      f.AddGTestTestStep('sync_unit_tests', fp)
    if R('unit_sync_br'):
      f.AddBuildrunnerGTest('sync_unit_tests', fp)
    if R('unit_unit', 'unit_tests'):
      f.AddGTestTestStep('unit_tests', fp)
    if R('unit_unit_br'):
      f.AddBuildrunnerGTest('unit_tests', fp)
    if R('unit_sql', 'sql_unittests'):
      f.AddGTestTestStep('sql_unittests', fp)
    if R('unit_sql_br'):
      f.AddBuildrunnerGTest('sql_unittests', fp)
    if R('browser_tests'):
      f.AddBrowserTests(fp)
    if R('browser_tests_br'):
      f.AddBuildrunnerBrowserTests(fp)
    if R('push_canary_tests'):
      f.AddPushCanaryTests(fp)
    if R('chromedriver_tests'):
      f.AddGTestTestStep('chromedriver_tests', fp)
    if R('chromedriver_tests_br'):
      f.AddBuildrunnerGTest('chromedriver_tests', fp)
    if R('content_browsertests'):
      f.AddGTestTestStep('content_browsertests', fp)
    if R('content_browsertests_br'):
      f.AddBuildrunnerGTest('content_browsertests', fp)
    if R('ash_browsertests'):
      ash_fp = fp.copy()
      ash_fp['browser_tests_extra_options'] = ['--ash-browsertests']
      f.AddBuildrunnerBrowserTests(ash_fp)

    # Big, UI tests:
    if R('dom_checker'):
      f.AddDomCheckerTests()
    if R('dom_checker_br'):
      f.AddBuildrunnerDomCheckerTests()

    if self._target_platform == 'win32':
      if R('installer_util_unittests'):
        f.AddGTestTestStep('installer_util_unittests', fp)
      if R('installer_util_unittests_br'):
        f.AddBuildrunnerGTest('installer_util_unittests', fp)

    if R('installer'):
      f.AddInstallerTests(fp)
    if R('installer_br'):
      f.AddBuildrunnerInstallerTests(fp)

    if R('mini_installer'):
      f.AddMiniInstallerTestStep(fp)

    # WebKit-related tests:
    if R('webkit_compositor_bindings_unittests'):
      f.AddGTestTestStep('webkit_compositor_bindings_unittests', fp)
    if R('webkit_compositor_bindings_unittests_br'):
      f.AddBuildrunnerGTest('webkit_compositor_bindings_unittests', fp)
    if R('webkit_unit_tests'):
      f.AddGTestTestStep('webkit_unit_tests', fp)
    if R('webkit_unit_br'):
      f.AddBuildrunnerGTest('webkit_unit_tests', fp)
    if R('wtf_unittests'):
      f.AddGTestTestStep('wtf_unittests', fp)
    if R('wtf_unittests_br'):
      f.AddBuildrunnerGTest('wtf_unittests', fp)
    if R('blink_platform_unittests'):
      f.AddGTestTestStep('blink_platform_unittests', fp)
    if R('blink_platform_unittests_br'):
      f.AddBuildrunnerGTest('blink_platform_unittests', fp)
    if R('webkit_lint'):
      f.AddWebkitLint(factory_properties=fp)
    if R('webkit_lint_br'):
      f.AddBuildrunnerWebkitLint(factory_properties=fp)
    if R('webkit_python_tests'):
      f.AddWebkitPythonTests(factory_properties=fp)
    if R('webkit_python_tests_br'):
      f.AddBuildrunnerWebkitPythonTests(factory_properties=fp)
    if R('webkit'):
      f.AddWebkitTests(factory_properties=fp)
    if R('devtools_perf'):
      f.AddDevToolsTests(factory_properties=fp)

    # Android device test
    if R('device_status'):
      f.AddDeviceStatus(factory_properties=fp)

    def Telemetry(test_name):
      if R(test_name.replace('.', '_')):
        f.AddTelemetryTest(test_name, factory_properties=fp)

    # Benchmark tests:
    # Page cyclers:
    page_cyclers = (
        'bloat',
        'dhtml',
        'indexeddb',
        'morejs',
        'moz',

        'intl_ar_fa_he',
        'intl_es_fr_pt-BR',
        'intl_hi_ru',
        'intl_ja_zh',
        'intl_ko_th_vi',

        'pica',
        'tough_layout_cases',
        'typical_25',

        'top_10_mobile',
        'netsim.top_10',
      )
    for test_name in page_cyclers:
      Telemetry('page_cycler.' + test_name)

    # Synthetic benchmarks:
    synthetic_benchmarks = (
        'dom_perf',
        'jsgamebench',
        'kraken',
        'octane',
        'robohornet_pro',
        'spaceport',
        'sunspider',

        'image_decoding.tough_decoding_cases',
        'media.tough_media_cases',
      )
    for test_name in synthetic_benchmarks:
      Telemetry(test_name)
    if R('blink_perf'):
      f.AddTelemetryTest('blink_perf', factory_properties=fp)
      f.AddTelemetryTest('blink_perf.web_animations', factory_properties=fp)
    if R('dromaeo'):
      dromaeo_benchmarks = (
          'domcoreattr',
          'domcoremodify',
          'domcorequery',
          'domcoretraverse',
          'jslibattrjquery',
          'jslibattrprototype',
          'jslibeventjquery',
          'jslibeventprototype',
          'jslibmodifyjquery',
          'jslibmodifyprototype',
          'jslibstylejquery',
          'jslibstyleprototype',
          'jslibtraversejquery',
          'jslibtraverseprototype',
        )
      for test_name in dromaeo_benchmarks:
        f.AddTelemetryTest('dromaeo.%s' % test_name, factory_properties=fp)

    # Real-world benchmarks:
    real_world_benchmarks = (
        'maps',
        'memory.reload.2012Q3',
        'memory.top_25',
        'rasterize_and_record.key_mobile_sites',
        'rasterize_and_record.top_25',
        'smoothness.key_mobile_sites',
        'smoothness.top_25',
        'smoothness.tough_canvas_cases',
        'tab_switching.top_10',
      )
    for test_name in real_world_benchmarks:
      Telemetry(test_name)

    # Other benchmarks:
    if R('memory'):
      f.AddMemoryTests(fp)
    if R('gpu_throughput'):
      f.AddGpuThroughputTests(fp)
    if R('tab_capture_performance'):
      f.AddTabCapturePerformanceTests(fp)
    if R('idb_perf'):
      f.AddIDBPerfTests(fp)
    if R('shutdown'):
      f.AddShutdownTests(fp)
    if R('startup_cold'):
      f.AddTelemetryTest('startup.cold.blank_page', factory_properties=fp)
    if R('startup_warm'):
      f.AddTelemetryTest('startup.warm.blank_page', factory_properties=fp)
    if R('startup_warm_dirty'):
      startup_fp = fp.copy()
      # pylint: disable=W0212
      startup_fp['profile_type'] = 'small_profile'
      f.AddTelemetryTest('startup.warm.blank_page',
                         step_name='startup.warm.dirty.blank_page',
                         factory_properties=startup_fp)
    if R('startup_cold_dirty'):
      startup_fp = fp.copy()
      # pylint: disable=W0212
      startup_fp['profile_type'] = 'small_profile'
      f.AddTelemetryTest('startup.cold.blank_page',
                         step_name='startup.cold.dirty.blank_page',
                         factory_properties=startup_fp)
    if R('startup_warm_session_restore'):
      startup_fp = fp.copy()
      # pylint: disable=W0212
      startup_fp['profile_type'] = 'small_profile'
      f.AddTelemetryTest('session_restore.warm.typical_25',
                         step_name='session_restore.warm.typical_25',
                         factory_properties=startup_fp)
    if R('startup_cold_session_restore'):
      startup_fp = fp.copy()
      # pylint: disable=W0212
      startup_fp['profile_type'] = 'small_profile'
      f.AddTelemetryTest('session_restore.cold.typical_25',
                         step_name='session_restore.cold.typical_25',
                         factory_properties=startup_fp)


    if R('sizes'):
      f.AddSizesTests(fp)
    if R('sizes_br'):
      f.AddBuildrunnerSizesTests(fp)
    if R('sync'):
      f.AddSyncPerfTests(fp)
    if R('mach_ports'):
      f.AddMachPortsTests(fp)
    if R('cc_perftests'):
      f.AddCCPerfTests(fp)
    if R('media_perftests'):
      f.AddMediaPerfTests(fp)

    if R('sync_integration'):
      f.AddSyncIntegrationTests(fp)
    if R('sync_integration_br'):
      f.AddBuildrunnerSyncIntegrationTests(fp)

    # WebRTC tests:
    if R('webrtc_perf_content_unittests'):
      f.AddWebRtcPerfContentUnittests(fp)
    if R('webrtc_manual_content_browsertests'):
      arg_list = ['--gtest_filter=WebRTC*:Webrtc*:*Dtmf', '--run-manual']
      f.AddGTestTestStep('content_browsertests', description=' (manual)',
                         factory_properties=fp, arg_list=arg_list)
    if R('webrtc_content_unittests'):
      arg_list = ['--gtest_filter=WebRTC*:RTC*:MediaStream*']
      f.AddGTestTestStep('content_unittests', description=' (webrtc filtered)',
                         factory_properties=fp, arg_list=arg_list)
    if R('webrtc_manual_browser_tests'):
      f.AddWebRtcPerfManualBrowserTests(fp)

    # GPU tests:
    if R('gl_tests'):
      f.AddGLTests(fp)
    if R('gl_tests_br'):
      f.AddBuildrunnerGTest('gl_tests', fp, test_tool_arg_list=['--no-xvfb'])
    if R('content_gl_tests'):
      f.AddContentGLTests(fp)
    if R('gles2_conform_test'):
      f.AddGLES2ConformTest(fp)
    if R('gles2_conform_test_br'):
      f.AddBuildrunnerGTest('gles2_conform_test', fp,
                            test_tool_arg_list=['--no-xvfb'])
    if R('gpu_content_tests'):
      f.AddGpuContentTests(fp)

    # ChromeFrame tests:
    if R('chrome_frame_perftests'):
      f.AddChromeFramePerfTests(fp)
    if R('chrome_frame'):
      # Add all major CF tests.
      f.AddGTestTestStep('chrome_frame_net_tests', fp)
      f.AddGTestTestStep('chrome_frame_unittests', fp)
      f.AddGTestTestStep('chrome_frame_tests', fp)
    elif R('chrome_frame_br'):
      f.AddBuildrunnerGTest('chrome_frame_net_tests', fp)
      f.AddBuildrunnerGTest('chrome_frame_unittests', fp)
      f.AddBuildrunnerGTest('chrome_frame_tests', fp)
    else:
      if R('chrome_frame_net_tests'):
        f.AddGTestTestStep('chrome_frame_net_tests', fp)
      if R('chrome_frame_net_tests_br'):
        f.AddBuildrunnerGTest('chrome_frame_net_tests', fp)
      if R('chrome_frame_unittests'):
        f.AddGTestTestStep('chrome_frame_unittests', fp)
      if R('chrome_frame_unittests_br'):
        f.AddBuildrunnerGTest('chrome_frame_unittests', fp)
      if R('chrome_frame_tests'):
        f.AddGTestTestStep('chrome_frame_tests', fp)
      if R('chrome_frame_tests_br'):
        f.AddBuildrunnerGTest('chrome_frame_tests', fp)

    def S(test, prefix, add_functor, br_functor=None):
      """Find any tests with a specific prefix and add them to the build.

      S() looks for prefix attached to a test, strips the prefix, and performs a
      prefix-specific add function via add_functor. If the test is also a
      buildrunner test (ends in _br), it uses a buildrunner functor. Thus,
      instead of ash_unittests, valgrind_ash_unittests is ash_unittests added
      with a special function (one that wraps it with a valgrind driver.
      """
      if test.startswith(prefix):
        test_name = test[len(prefix):]
        tests.remove(test)
        if br_functor and test_name.endswith('_br'):
          br_functor(test_name[:-3])
        else:
          add_functor(test_name)
        return True

    def M(test, prefix, test_type, fp):
      """A special case of S() that operates on memory tests."""
      return S(
          test, prefix, lambda test_name:
          f.AddMemoryTest(test_name, test_type, factory_properties=fp),
          lambda test_name:
            f.AddBuildrunnerMemoryTest(
                test_name, test_type, factory_properties=fp))

    # Valgrind tests:
    for test in tests[:]:
      # TODO(timurrrr): replace 'valgrind' with 'memcheck'
      #                 below and in master.chromium/master.cfg
      if M(test, 'valgrind_', 'memcheck', fp):
        continue
      # Run TSan in two-stage RaceVerifier mode.
      if M(test, 'tsan_rv_', 'tsan_rv', fp):
        continue
      if M(test, 'tsan_', 'tsan', fp):
        continue
      if M(test, 'drmemory_light_', 'drmemory_light', fp):
        continue
      if M(test, 'drmemory_full_', 'drmemory_full', fp):
        continue
      if M(test, 'drmemory_pattern_', 'drmemory_pattern', fp):
        continue
      if S(test, 'heapcheck_',
           lambda name: f.AddHeapcheckTest(name,
                                           timeout=1200,
                                           factory_properties=fp)):
        continue

    # Endurance tests.
    def FP(test_name):
      """A factory properties copy including test-specific properties."""
      if fp.has_key('test_properties'):
        return dict(fp, **fp['test_properties'].get(test_name, {}))
      else:
        return fp.copy()

    def Endure(test_name, telemetry_test_name, test_name_ui):
      """Adds an endurance test if configured."""
      if R(test_name):
        # Get test-specific factory properties.
        test_fp = FP(test_name)
        # Test name for waterfall ui and dashboard.
        full_test_name = '%s%s' % (test_name_ui,
                                   test_fp.get('test_name_suffix', ''))
        # Hierarchical suite + test name only for dashboard. The 'step_name'
        # is passed to runtest.py, where it is used to build the test name on
        # the archive and dashboard.
        test_fp['step_name'] = 'endure/%s' % full_test_name

        f.AddTelemetryTest(
            telemetry_test_name,
            step_name='endure_%s' % full_test_name,
            factory_properties=test_fp,
            timeout=6000)

    Endure('endure_calendar_tests',
           'endure.calendar_forward_backward',
           'cal_fw_back')

    Endure('endure_gmail_expand_collapse_tests',
           'endure.gmail_expand_collapse_conversation',
           'gmail_exp_col')

    Endure('endure_gmail_alt_label_tests',
           'endure.gmail_alt_two_labels',
           'gmail_labels')

    Endure('endure_gmail_alt_threadlist_tests',
           'endure.gmail_alt_threadlist_conversation',
           'gmail_thread')

    Endure('endure_plus_tests',
           'endure.plus_alt_posts_photos',
           'plus_photos')

    # HTML5 media tag performance/functional test using PyAuto.
    if R('avperf'):
      # Performance test should be run on virtual X buffer.
      fp['use_xvfb_on_linux'] = True
      f.AddMediaTests(factory_properties=fp, test_groups=self.MEDIA_TEST_GROUPS)
    if R('chromedriver_tests'):
      f.AddChromeDriverTest()
    if R('webdriver_tests'):
      f.AddWebDriverTest()

    # Dynamorio coverage.
    if R('trigger_coverage_tests'):
      f.AddTriggerCoverageTests(fp)
    if R('extract_dynamorio_build'):
      f.AddExtractDynamorioBuild(fp)
    if R('coverage_tests'):
      f.AddCoverageTests(fp)

    # When adding a test that uses a new executable, update kill_processes.py.

    # Coverage tests.  Add coverage processing absoluely last, after
    # all tests have run.  Tests which run after coverage processing
    # don't get counted.
    if R('process_coverage'):
      f.AddProcessCoverage(fp)

    # Add nacl integration tests (do these toward the end as they use the
    # annotator).
    if R('nacl_integration'):
      f.AddNaClIntegrationTestStep(fp)
    if R('nacl_integration_br'):
      f.AddBuildrunnerNaClIntegrationTestStep(fp)
    if R('nacl_integration_memcheck'):
      f.AddNaClIntegrationTestStep(fp, None, 'memcheck-browser-tests')
    if R('nacl_integration_tsan'):
      f.AddNaClIntegrationTestStep(fp, None, 'tsan-browser-tests')

    if R('buildrunner_tests'):
      f.AddBuildStep(factory_properties, name='buildrunner_tests')

    # Add bisection test (if this is specified, it should be the only test)
    if R('bisect_revisions'):
      f.AddBisectTest()

    # Add an optional set of annotated steps.
    # NOTE: This really should go last as it can be confusing if the annotator
    # isn't the last thing to run.
    if R('annotated_steps'):
      f.AddAnnotatedSteps(fp)

    # If this assert triggers and the test name is valid, make sure R() is used.
    # If you are using a subclass, make sure the tests list provided to
    # _AddTests() had the factory-specific tests stripped off.
    assert not tests, 'Did you make a typo? %s wasn\'t processed' % tests

  @property
  def build_dir(self):
    return self._build_dir

  def ForceMissingFilesToBeFatal(self, project, gclient_env):
    """Force Windows bots to fail GYPing if referenced files do not exist."""
    gyp_generator_flags = gclient_env.setdefault('GYP_GENERATOR_FLAGS', '')
    if (self._target_platform == 'win32' and
        'msvs_error_on_missing_sources=' not in gyp_generator_flags):
      gclient_env['GYP_GENERATOR_FLAGS'] = (
          gyp_generator_flags + ' msvs_error_on_missing_sources=1')

  def ChromiumFactory(self, target='Release', clobber=False, tests=None,
                      mode=None, slave_type='BuilderTester',
                      options=None, compile_timeout=1200, build_url=None,
                      project=None, factory_properties=None, gclient_deps=None,
                      run_default_swarm_tests=None):
    factory_properties = (factory_properties or {}).copy()
    run_default_swarm_tests = run_default_swarm_tests or []

    # Default to the configuration of Blink appropriate for Chromium patches.
    factory_properties.setdefault('blink_config', 'chromium')
    if factory_properties['blink_config'] == 'blink':
      # This will let builders embed their webkit revision in their output
      # filename and will let testers look for zip files containing a webkit
      # revision in their filename. For this to work correctly, the testers
      # need to be on a Triggerable that's activated by their builder.
      factory_properties.setdefault('webkit_dir', 'third_party/WebKit/Source')

    factory_properties['gclient_env'] = \
        factory_properties.get('gclient_env', {}).copy()
    # Defaults gyp to VS2010.
    if self._target_platform == 'win32':
      factory_properties['gclient_env'].setdefault('GYP_MSVS_VERSION', '2010')
      FixForGomaWin(options, target, factory_properties['gclient_env'])
    tests = tests or []

    if factory_properties.get('needs_valgrind'):
      self._solutions[0].custom_deps_list = [self.CUSTOM_DEPS_VALGRIND]
    elif factory_properties.get('needs_tsan_win'):
      self._solutions[0].custom_deps_list = [self.CUSTOM_DEPS_TSAN_WIN]
    elif factory_properties.get('needs_drmemory'):
      if 'drmemory.DEPS' not in [s.name for s in self._solutions]:
        self._solutions.append(gclient_factory.GClientSolution(
            config.Master.trunk_url +
            '/deps/third_party/drmemory/drmemory.DEPS',
            'drmemory.DEPS'))
    elif factory_properties.get('needs_webdriver_java_tests'):
      self._solutions[0].custom_deps_list = [
        self.CUSTOM_DEPS_WEBDRIVER_JAVA_TESTS
      ]

    if 'devtools_perf' in tests:
      self._solutions[0].custom_deps_list.extend(self.CUSTOM_DEPS_DEVTOOLS_PERF)

    if factory_properties.get('safesync_url'):
      self._solutions[0].safesync_url = factory_properties.get('safesync_url')
    elif factory_properties.get('lkgr'):
      self._solutions[0].safesync_url = self.SAFESYNC_URL_CHROMIUM

    tests_for_build = [
        re.match('^(?:valgrind_|heapcheck_)?(.*)$', t).group(1) for t in tests]

    # Ensure that component is set correctly in the gyp defines.
    ForceComponent(target, project, factory_properties['gclient_env'])

    # Ensure GYP errors out if files referenced in .gyp files are missing.
    self.ForceMissingFilesToBeFatal(project, factory_properties['gclient_env'])

    # There's 2 different windows ASan builder:
    #     - The unittests builder, which build all the unittests, instrument
    #       them and put them in a zip file for the test bots.
    #     - The Chromium LKGR builder, which build the All_syzygy target of the
    #       Chromium project with the 'asan' gyp define set. There's no need to
    #       call a script to do the instrumentation for this target (it' already
    #       in the build steps). This builder should archive the builds for
    #       Clusterfuzz, it need to have the 'cf_archive_build' property.
    is_win_asan_tests_builder = (slave_type == 'Builder' and
                                 self._target_platform == 'win32' and
                                 factory_properties.get('asan') and
                                 not factory_properties.get('cf_archive_build'))

    factory = self.BuildFactory(target, clobber, tests_for_build, mode,
                                slave_type, options, compile_timeout, build_url,
                                project, factory_properties,
                                gclient_deps=gclient_deps,
                                skip_archive_steps=is_win_asan_tests_builder)

    # Get the factory command object to create new steps to the factory.
    chromium_cmd_obj = chromium_commands.ChromiumCommands(factory,
                                                          target,
                                                          self._build_dir,
                                                          self._target_platform)

    # Add ASANification step for windows unittests.
    # MUST BE FIRST STEP ADDED AFTER BuildFactory CALL in order to add back
    # the ZipBuild step in it's expected place.
    if is_win_asan_tests_builder:
      # This must occur before syzygy modifies the dlls.
      for dll in ['chrome.dll', 'chrome_child.dll']:
        chromium_cmd_obj.AddGenerateCodeTallyStep(dll)
        chromium_cmd_obj.AddConvertCodeTallyJsonStep(dll)

        if factory_properties.get('code_tally_upload_url'):
          chromium_cmd_obj.AddUploadConvertedCodeTally(
              dll, factory_properties.get('code_tally_upload_url'))

      chromium_cmd_obj.AddWindowsASANStep()
      # Need to add the Zip Build step back
      chromium_cmd_obj.AddZipBuild(halt_on_failure=True,
                                   factory_properties=factory_properties)

    # Add check/start step for virtual webcams, if needed.
    if factory_properties.get('virtual_webcam'):
      chromium_cmd_obj.AddVirtualWebcamCheck()

    # Add this archive build step.
    if factory_properties.get('archive_build'):
      chromium_cmd_obj.AddArchiveBuild(factory_properties=factory_properties)

    if factory_properties.get('cf_archive_build'):
      chromium_cmd_obj.AddCFArchiveBuild(
          factory_properties=factory_properties)

    # Add the package source step.
    if slave_type == 'Indexer':
      chromium_cmd_obj.AddPackageSource(factory_properties=factory_properties)

    # Add a trigger step if needed.
    self.TriggerFactory(factory, slave_type=slave_type,
                        factory_properties=factory_properties)

    if run_default_swarm_tests:
      # Trigger swarm tests. Extract all the swarm tests from |tests|. Note that
      # this only triggers the swarm job but do not add the steps to get the
      # results.
      swarm_tests = []
      for i in reversed(range(len(tests))):
        if tests[i].endswith('_swarm'):
          swarm_tests.append(tests.pop(i))
      chromium_cmd_obj.AddTriggerSwarmTests(
          swarm_tests, run_default_swarm_tests, factory_properties)

    # Start the crash handler process.
    if ((self._target_platform == 'win32' and slave_type != 'Builder' and
         self._build_dir == 'src/chrome') or
        factory_properties.get('start_crash_handler')):
      chromium_cmd_obj.AddRunCrashHandler()

    # Add all the tests.
    self._AddTests(chromium_cmd_obj, tests, mode, factory_properties)

    if factory_properties.get('process_dumps'):
      chromium_cmd_obj.AddProcessDumps()

    return factory

  def ChromiumAnnotationFactory(self, annotation_script,
                                branch='master',
                                target='Release',
                                slave_type='AnnotatedBuilderTester',
                                clobber=False,
                                compile_timeout=6000,
                                maxTime=8*60*60,
                                project=None,
                                factory_properties=None, options=None,
                                tests=None,
                                gclient_deps=None):
    """Annotation-driven Chromium buildbot factory.

    Like a ChromiumFactory, but non-sync steps (compile, run tests)
    are specified in a script that uses @@@BUILD_STEP descriptive
    text@@@ style annotations.

    Note new slave type AnnotatedBuilderTester; we don't want a
    compile step added.
    TODO(jrg): is a new slave type the right direction?
    """
    # Setup factory.
    factory_properties = factory_properties or {}
    options = options or {}
    if self._target_os:
      factory_properties['target_os'] = self._target_os

    # Ensure that component is set correctly in the gyp defines.
    ForceComponent(target, project, factory_properties)

    factory = self.BuildFactory(target=target, clobber=clobber,
                                tests=tests, mode=None, slave_type=slave_type,
                                options=options,
                                compile_timeout=compile_timeout, build_url=None,
                                project=project,
                                factory_properties=factory_properties,
                                gclient_deps=gclient_deps)

    # Get the factory command object to create new steps to the factory.
    chromium_cmd_obj = chromium_commands.ChromiumCommands(
        factory=factory,
        target=target,
        build_dir=self._build_dir,
        target_platform=self._target_platform,
        target_os=self._target_os)

    # Add the main build.
    env = factory_properties.get('annotation_env')
    factory_properties['target'] = target
    factory_properties.setdefault('clobber', clobber)

    chromium_cmd_obj.AddAnnotationStep(
        name='slave_steps',
        cmd=annotation_script,
        factory_properties=factory_properties,
        env=env, maxTime=maxTime)

    # Add archive build step.
    if factory_properties.get('archive_build'):
      chromium_cmd_obj.AddArchiveBuild(factory_properties=factory_properties)

    # Add all the tests.
    self._AddTests(factory_cmd_obj=chromium_cmd_obj, tests=tests,
                   factory_properties=factory_properties)

    # Add a trigger step if needed.
    self.TriggerFactory(factory, slave_type=slave_type,
                        factory_properties=factory_properties)

    return factory


  def ChromiumV8LatestFactory(self, target='Release', clobber=False, tests=None,
                              mode=None, slave_type='BuilderTester',
                              options=None, compile_timeout=1200,
                              build_url=None, project=None,
                              factory_properties=None):
    self._solutions[0].custom_deps_list = [self.CUSTOM_DEPS_V8_LATEST]
    return self.ChromiumFactory(target, clobber, tests, mode, slave_type,
                                options, compile_timeout, build_url, project,
                                factory_properties)
  def ChromiumV8TrunkFactory(self, target='Release', clobber=False, tests=None,
                             mode=None, slave_type='BuilderTester',
                             options=None, compile_timeout=1200,
                             build_url=None, project=None,
                             factory_properties=None):
    self._solutions[0].custom_deps_list = [self.CUSTOM_DEPS_V8_TRUNK]
    return self.ChromiumFactory(target, clobber, tests, mode, slave_type,
                                options, compile_timeout, build_url, project,
                                factory_properties)

  def ChromiumWebRTCFactory(self, target='Release', clobber=False,
                            tests=None, mode=None,
                            slave_type='BuilderTester', options=None,
                            compile_timeout=1200, build_url=None,
                            project=None, factory_properties=None):
    self._solutions.append(gclient_factory.GClientSolution(
        config.Master.trunk_url + '/deps/third_party/webrtc/webrtc.DEPS',
        name='webrtc.DEPS'))
    return self.ChromiumFactory(target, clobber, tests, mode, slave_type,
                                options, compile_timeout, build_url, project,
                                factory_properties)

  def ChromiumWebRTCLatestFactory(self, target='Release', clobber=False,
                                  tests=None, mode=None,
                                  slave_type='BuilderTester', options=None,
                                  compile_timeout=1200, build_url=None,
                                  project=None, factory_properties=None):
    self._solutions[0].custom_deps_list = [self.CUSTOM_DEPS_WEBRTC_TRUNK,
                                           self.CUSTOM_DEPS_LIBJINGLE_TRUNK]
    factory_properties = factory_properties or {}
    factory_properties['primary_repo'] = 'webrtc_'
    factory_properties['no_gclient_revision'] = True
    factory_properties['revision_dir'] = 'third_party/webrtc'
    return self.ChromiumWebRTCFactory(target, clobber, tests, mode, slave_type,
                                      options, compile_timeout, build_url,
                                      project, factory_properties)

  def ChromiumWebRTCAndroidFactory(self, annotation_script,
                                   branch='master',
                                   target='Release',
                                   slave_type='AnnotatedBuilderTester',
                                   clobber=False,
                                   compile_timeout=6000,
                                   project=None,
                                   factory_properties=None, options=None,
                                   tests=None,
                                   gclient_deps=None):
    self._solutions[0].custom_deps_list = [self.CUSTOM_DEPS_WEBRTC_TRUNK,
                                           self.CUSTOM_DEPS_LIBJINGLE_TRUNK]
    self._solutions.append(gclient_factory.GClientSolution(
        config.Master.trunk_url + '/deps/third_party/webrtc/webrtc.DEPS',
        name='webrtc.DEPS'))
    factory_properties = factory_properties or {}
    factory_properties['primary_repo'] = 'webrtc_'
    factory_properties['no_gclient_revision'] = True
    factory_properties['revision_dir'] = 'third_party/webrtc'
    return self.ChromiumAnnotationFactory(annotation_script=annotation_script,
                                          branch=branch,
                                          target=target,
                                          slave_type=slave_type,
                                          clobber=clobber,
                                          compile_timeout=compile_timeout,
                                          project=project,
                                          factory_properties=factory_properties,
                                          options=options,
                                          tests=tests,
                                          gclient_deps=gclient_deps)

  def ChromiumAVPerfFactory(self, target='Release', clobber=False, tests=None,
                              mode=None, slave_type='BuilderTester',
                              options=None, compile_timeout=1200,
                              build_url=None, project=None,
                              factory_properties=None):
    self._solutions[0].custom_deps_list = [self.CUSTOM_DEPS_AVPERF]
    return self.ChromiumFactory(target, clobber, tests, mode, slave_type,
                                options, compile_timeout, build_url, project,
                                factory_properties)

  def ChromiumNativeClientLatestFactory(
      self, target='Release', clobber=False, tests=None, mode=None,
      slave_type='BuilderTester', options=None, compile_timeout=1200,
      build_url=None, project=None, factory_properties=None,
      on_nacl_waterfall=True, use_chrome_lkgr=True):
    factory_properties = factory_properties or {}
    if on_nacl_waterfall:
      factory_properties['primary_repo'] = 'nacl_'
    # Remove nacl_trunk variable.
    self._solutions[0].custom_vars_list = [
      v for v in self._solutions[0].custom_vars_list if v[0] != 'nacl_trunk'
    ]
    self._solutions[0].custom_vars_list.extend(self.CUSTOM_VARS_NACL_LATEST)
    self._solutions[0].safesync_url = self.SAFESYNC_URL_CHROMIUM
    if factory_properties.get('needs_nacl_valgrind'):
      self._solutions[0].custom_deps_list.append(self.CUSTOM_DEPS_NACL_VALGRIND)
    return self.ChromiumFactory(target, clobber, tests, mode, slave_type,
                                options, compile_timeout, build_url, project,
                                factory_properties)

  def ChromiumGYPLatestFactory(self, target='Debug', clobber=False, tests=None,
                               mode=None, slave_type='BuilderTester',
                               options=None, compile_timeout=1200,
                               build_url=None, project=None,
                               factory_properties=None, gyp_format=None):

    if tests is None:
      tests = ['unit']

    if gyp_format:
      # Set GYP_GENERATORS in the environment used to execute
      # gclient so we get the right build tool configuration.
      if factory_properties is None:
        factory_properties = {}
      gclient_env = factory_properties.get('gclient_env', {})
      gclient_env['GYP_GENERATORS'] = gyp_format
      factory_properties['gclient_env'] = gclient_env

      # And tell compile.py what build tool to use.
      if options is None:
        options = []
      options.append('--build-tool=' + gyp_format)

    self._solutions[0].custom_deps_list = self.CUSTOM_DEPS_GYP
    return self.ChromiumFactory(target, clobber, tests, mode, slave_type,
                                options, compile_timeout, build_url, project,
                                factory_properties)

  def ChromiumArmuFactory(self, target='Release', clobber=False, tests=None,
                          mode=None, slave_type='BuilderTester', options=None,
                          compile_timeout=1200, build_url=None, project=None,
                          factory_properties=None):
    self._project = 'webkit_armu.sln'
    self._solutions[0].custom_deps_list = [self.CUSTOM_DEPS_V8_LATEST]
    return self.ChromiumFactory(target, clobber, tests, mode, slave_type,
                                options, compile_timeout, build_url, project,
                                factory_properties)

  def ChromiumOSFactory(self, target='Release', clobber=False, tests=None,
                        mode=None, slave_type='BuilderTester', options=None,
                        compile_timeout=1200, build_url=None, project=None,
                        factory_properties=None):
    # Make sure the solution is not already there.
    if 'cros_deps' not in [s.name for s in self._solutions]:
      self._solutions.append(gclient_factory.GClientSolution(
          config.Master.trunk_url + '/src/tools/cros.DEPS', name='cros_deps'))

    return self.ChromiumFactory(target, clobber, tests, mode, slave_type,
                                options, compile_timeout, build_url, project,
                                factory_properties)

  def ChromiumBranchFactory(
      self, target='Release', clobber=False, tests=None, mode=None,
      slave_type='BuilderTester', options=None, compile_timeout=1200,
      build_url=None, project=None, factory_properties=None,
      trunk_src_url=None):
    self._solutions = [gclient_factory.GClientSolution(trunk_src_url, 'src')]
    return self.ChromiumFactory(target, clobber, tests, mode, slave_type,
                                options, compile_timeout, build_url, project,
                                factory_properties)

  def ChromiumGPUFactory(self, target='Release', clobber=False, tests=None,
                         mode=None, slave_type='Tester', options=None,
                         compile_timeout=1200, build_url=None, project=None,
                         factory_properties=None):
    # Make sure the solution is not already there.
    if 'gpu_reference.DEPS' not in [s.name for s in self._solutions]:
      self._solutions.append(gclient_factory.GClientSolution(
          config.Master.trunk_url + '/deps/gpu_reference/gpu_reference.DEPS',
          'gpu_reference.DEPS'))
    return self.ChromiumFactory(target, clobber, tests, mode, slave_type,
                                options, compile_timeout, build_url, project,
                                factory_properties)

  def ChromiumASANFactory(self, target='Release', clobber=False, tests=None,
                          mode=None, slave_type='BuilderTester', options=None,
                          compile_timeout=1200, build_url=None, project=None,
                          factory_properties=None):
    return self.ChromiumFactory(target, clobber, tests, mode, slave_type,
                                options, compile_timeout, build_url, project,
                                factory_properties)

  def ChromiumCodesearchFactory(self, target='Release', clobber=False,
                                tests=None, mode=None,
                                slave_type='BuilderTester', options=None,
                                compile_timeout=1200, build_url=None,
                                project=None, factory_properties=None):
    # Make sure the solution is not already there.
    assert 'clang_indexer.DEPS' not in [s.name for s in self._solutions]
    self._solutions.append(gclient_factory.GClientSolution(
        'svn://svn.chromium.org/chrome-internal/trunk/deps/'
        'clang_indexer.DEPS'))
    return self.ChromiumFactory(target, clobber, tests, mode, slave_type,
                                options, compile_timeout, build_url, project,
                                factory_properties)

  def ChromiumGitFactory(self, target='Release', clobber=False, tests=None,
                      mode=None, slave_type='BuilderTester',
                      options=None, compile_timeout=1200, build_url=None,
                      project=None, factory_properties=None, gclient_deps=None,
                      run_default_swarm_tests=None, git_url=None,
                      pure_git=False):
    if not factory_properties:
      factory_properties = {}
    factory_properties['no_gclient_branch'] = True

    # Overwrite the default svn gclient solutions with git ones.
    git_url = '%s/chromium/src.git' % config.Master.git_server_url
    self._solutions[0].svn_url = git_url
    #TODO(agable): remove custom_deps_file when .DEPS.git is deprecated.
    if pure_git:
      self._solutions[0].custom_deps_file = '.DEPS.git'

    if (len(self._solutions) > 1 and
        self._solutions[1].svn_url == config.Master.trunk_internal_url_src):
      git_url = ('%s/chrome/src-internal.git' %
                 config.Master.git_internal_server_url)
      self._solutions[1].svn_url = git_url
      #TODO(agable): remove custom_deps_file when .DEPS.git is deprecated.
      if pure_git:
        self._solutions[1].custom_deps_file = '.DEPS.git'
      self._solutions[1].custom_deps_list = self.CUSTOM_DEPS_GIT_INTERNAL

    return self.ChromiumFactory(target, clobber, tests, mode, slave_type,
                                options, compile_timeout, build_url, project,
                                factory_properties, gclient_deps,
                                run_default_swarm_tests)

  def ChromiumOSASANFactory(self, target='Release', clobber=False, tests=None,
                            mode=None, slave_type='BuilderTester', options=None,
                            compile_timeout=1200, build_url=None, project=None,
                            factory_properties=None):
    # Make sure the solution is not already there.
    if 'cros_deps' not in [s.name for s in self._solutions]:
      self._solutions.append(gclient_factory.GClientSolution(
          config.Master.trunk_url + '/src/tools/cros.DEPS', name='cros_deps'))
    return self.ChromiumFactory(target, clobber, tests, mode, slave_type,
                                options, compile_timeout, build_url, project,
                                factory_properties)
