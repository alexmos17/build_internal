# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


DEPS = [
  'gclient',
  'git',
  'path',
  'platform',
  'properties',
  'python',
  'step',
]


REPOS = (
  'polymer',
  'platform',
  'CustomElements',
  'ShadowDOM',
  'HTMLImports',
  'observe-js',
  'NodeBind',
  'TemplateBinding',
  'polymer-expressions',
  'PointerGestures',
  'PointerEvents',
)


def _CheckoutSteps(api):
  repo_url = api.properties['repository']
  url_base = 'https://github.com/Polymer/'
  assert repo_url.startswith(url_base)
  repo = repo_url[len(url_base):]


  cfg = api.gclient.make_config()
  cfg.checkouts = [repo]
  for name in REPOS:
    soln = cfg.solutions.add()
    soln.name = name
    soln.url = url_base + name + '.git'
    soln.deps_file = ''

  submodule_command = api.python(
      'submodule update', api.path.depot_tools('gclient.py'),
      ['recurse', 'git', 'submodule', 'update', '--init', '--recursive'])

  return (
      api.gclient.checkout(cfg),
      submodule_command
  )


def GenSteps(api):

  if api.properties['repository'].rsplit('/', 1)[1] in [
      'observe-js', 'NodeBind', 'TemplateBinding', 'polymer-expressions']:
    return

  yield _CheckoutSteps(api)

  tmp_path = ''
  tmp_args = []
  if not api.platform.is_win:
    tmp_path = api.path.slave_build('.tmp')
    yield api.path.makedirs('tmp', tmp_path)
    tmp_args = ['--tmp', tmp_path]

  cmd_suffix = ''
  node_env = {}
  if api.platform.is_win:
    cmd_suffix = '.cmd'
    node_env = {'PATH': r'C:\Program Files (x86)\nodejs;'
                        r'C:\Users\chrome-bot\AppData\Roaming\npm;'
                        r'%(PATH)s'}

  test_prefix = []
  if api.platform.is_linux:
    test_prefix = ['xvfb-run']

  yield api.step('update-install', ['npm' + cmd_suffix, 'install'] + tmp_args,
                 cwd=api.path.checkout(), env=node_env)

  yield api.step('test', test_prefix + ['grunt' + cmd_suffix,
                 'test-buildbot'], cwd=api.path.checkout(),
                 env=node_env, allow_subannotations=True)


def GenTests(api):
  for plat in ('mac', 'linux', 'win'):
    yield 'polymer-%s' % plat, {
      'properties': api.properties_scheduled(
          repository='https://github.com/Polymer/polymer'),
      'mock': {
        'platform': {
            'name': plat
        }
      },
    }

  for proj in ['observe-js', 'NodeBind', 'TemplateBinding',
      'polymer-expressions']:
    yield 'polymer-%s' % proj, {
      'properties': api.properties_scheduled(
        repository='https://github.com/Polymer/%s' % proj),
      'mock': {
        'repository': 'https://github.com/Polymer/%s' % proj
      },
    }
