#!/usr/bin/env python
# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Helper script for fully-annotated builds. Performs checkouts of various
kinds.

This script is part of the effort to move all builds to annotator-based systems.
Any builder configured to use the AnnotatorFactory uses run.py as its entry
point. If that builder's factory_properties include a spec for a checkout, then
the work of actually performing that checkout is done here.
"""

import optparse
import os
import subprocess
import sys
import pipes

from common import annotator
from common import chromium_utils


SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__))


def get_args():
  """Process command-line arguments."""
  parser = optparse.OptionParser(
      description='Checkout helper for annotated builds.')
  parser.add_option('--type',
                    action='store', type='string', default='',
                    help='type of checkout (i.e. gclient, git, or svn)')
  parser.add_option('--spec',
                    action='callback', callback=chromium_utils.convert_json,
                    type='string', default={},
                    help='repository spec (url and metadata) to checkout')
  return parser.parse_args()


class _CheckoutMetaclass(type):
  """Automatically register Checkout subclasses for factory discoverability."""
  checkout_registry = {}

  def __new__(mcs, name, bases, attrs):
    checkout_type = attrs['CHECKOUT_TYPE']

    if checkout_type in mcs.checkout_registry:
      raise ValueError('Duplicate checkout identifier "%s" found in: %s' %
                       (checkout_type, name))

    # Only the base class is allowed to have no CHECKOUT_TYPE. The base class
    # should be the only one to specify this metaclass.
    if not checkout_type and attrs.get('__metaclass__') != mcs:
      raise ValueError('"%s" CHECKOUT_TYPE cannot be empty or None.' % name)

    newcls = super(_CheckoutMetaclass, mcs).__new__(mcs, name, bases, attrs)
    # Don't register the base class.
    if checkout_type:
      mcs.checkout_registry[checkout_type] = newcls
    return newcls


class Checkout(object):
  """Base class for implementing different types of checkouts.

  Attributes:
    CHECKOUT_TYPE: String identifier used when selecting the type of checkout to
        perform. All subclasses must specify a unique CHECKOUT_TYPE value.
  """
  __metaclass__ = _CheckoutMetaclass
  CHECKOUT_TYPE = None

  def __init__(self, spec):
    self.spec = spec

  def clean(self):
    pass

  def checkout(self):
    pass

  def root(self):
    pass


def CheckoutFactory(type_name, spec):
  """Factory to build Checkout class instances."""
  class_ = _CheckoutMetaclass.checkout_registry.get(type_name)
  if not class_ or not issubclass(class_, Checkout):
    raise KeyError('unrecognized checkout type: %s' % type_name)
  return class_(spec)


class GclientCheckout(Checkout):
  CHECKOUT_TYPE = 'gclient'

  gclient_path = os.path.abspath(
    os.path.join(SCRIPT_PATH, '..', '..', '..', 'depot_tools', 'gclient'))
  if sys.platform.startswith('win'):
    gclient_path += '.bat'

  def __init__(self, *args, **kwargs):
    super(GclientCheckout, self).__init__(*args, **kwargs)
    assert 'solutions' in self.spec
    spec_string = ''
    for key in self.spec:
      # We should be using json.dumps here, but gclient directly execs the dict
      # that it receives as the argument to --spec, so we have to have True,
      # False, and None instead of JSON's true, false, and null.
      spec_string += '%s = %s\n' % (key, str(self.spec[key]))
    self.run_gclient('config', '--spec', spec_string)

  @classmethod
  def run_gclient(cls, *cmd):
    print 'Running: gclient %s' % ' '.join(pipes.quote(x) for x in cmd)
    subprocess.check_call((cls.gclient_path,)+cmd)

  def clean(self):
    self.run_gclient('revert', '--nohooks')

  def checkout(self):
    self.run_gclient('sync', '--nohooks')

  def root(self):
    return os.path.abspath(self.spec['solutions'][0]['name'])


class GclientGitCheckout(GclientCheckout):
  """A gclient checkout tuned for purely git-based DEPS."""
  CHECKOUT_TYPE = 'gclient_git'
  def clean(self):
    # clean() isn't used because the gclient sync flags passed in checkout() do
    # much the same thing, and they're more correct than doing a separate
    # 'gclient revert' because it makes sure the other args are correct when a
    # repo was deleted and needs to be re-cloned (notably --with_branch_heads),
    # whereas 'revert' uses default args for clone operations.
    #
    # TODO(mmoss): To be like current official builders, this step could just
    # delete the whole <slave_name>/build/ directory and start each build from
    # scratch. That might be the least bad solution, at least until we have a
    # reliable gclient method to produce a pristine working dir for git-based
    # builds (e.g. maybe some combination of 'git reset/clean -fx' and removing
    # the 'out' directory).
    pass

  def checkout(self):
    self.run_gclient('sync', '--verbose', '--with_branch_heads', '--nohooks',
                     '--reset', '--delete_unversioned_trees', '--force')


class GitCheckout(Checkout):
  """Git specs are a dictionary with up to four keys: |url|, |branch|,
  |recursive|, and |directory|. Only |url| is required. The others default
  to empty, which results in using the git-default values of HEAD, False,
  and the 'humanish' interpretation of the url, respectively. Note that |url|
  is the full git url of the repo, including username and port number if
  necessary."""
  CHECKOUT_TYPE = 'git'

  def __init__(self, *args, **kwargs):
    super(GitCheckout, self).__init__(*args, **kwargs)
    assert 'url' in self.spec
    assert os.pardir not in self.spec.get('directory', '')

    dir_path = self.spec.get('directory')
    if not dir_path:
      dir_path = self.spec['url'].rsplit('/', 1)[-1]
      if dir_path.endswith('.git'):  # ex: https://host/foobar.git
        dir_path = dir_path[:-len('.git')]
      if not dir_path:  # ex: ssh://host:repo/foobar/.git
        dir_path = dir_path.rsplit('/', 1)[-1]
    self.cwd = os.path.abspath(os.path.join(os.curdir, dir_path))
    if not os.path.exists(self.cwd):
      os.makedirs(self.cwd)

    try:
      self.run_git('branch')
      exists = True
    except subprocess.CalledProcessError:
      exists = False
    if exists:
      self.run_git('remote', 'remove', 'origin')
    else:
      self.run_git('init')
    self.run_git('remote', 'add', 'origin', self.spec['url'])
    # TODO(agable): add support for git crup.
    if self.spec.get('recursive'):
      self.run_git('fetch', 'origin', '--recurse-submodules')
    else:
      self.run_git('fetch', 'origin')
    branch = self.spec.get('branch', 'master')
    self.run_git('update-ref', 'refs/heads/%s' % branch, 'origin/%s' % branch)

  def run_git(self, cmd, *args):
    cmd = (os.path.join(self.cwd, '.git'), '--work-tree', self.cwd) + cmd
    print 'Running: git %s %s' % (cmd, ' '.join(pipes.quote(x) for x in args))
    subprocess.check_call(['git', '--git-dir', cmd] + list(args))

  def clean(self):
    self.run_git('clean', '-f', '-d', '-x')

  def checkout(self):
    self.run_git('checkout', '-f', self.spec.get('branch', 'master'))

  def root(self):
    return os.path.basename(self.cwd)


class SvnCheckout(Checkout):
  CHECKOUT_TYPE = 'svn'


def run(checkout_type, checkout_spec):
  """Perform a checkout with the given type and configuration.

    Args:
      checkout_type: Type of checkout to perform (matching a Checkout subclass
          CHECKOUT_TYPE attribute).
      checkout_spec: Configuration values needed for the type of checkout
          (repository url, etc.).

    Returns:
      Tuple of (<retcode>, <root_path>) where root_path is the absolute path
          to the 'root' of the checkout (as defined by |checkout_type|).
  """
  stream = annotator.StructuredAnnotationStream(
      seed_steps=['checkout_setup', 'clean', 'checkout'])
  with stream.step('checkout_setup') as s:
    try:
      checkout = CheckoutFactory(checkout_type, checkout_spec)
    except KeyError as e:
      s.step_text(e)
      s.step_failure()
      return (1, None)
  with stream.step('clean') as s:
    checkout.clean()
  with stream.step('checkout') as s:
    checkout.checkout()
  return (0, checkout.root())


def main():
  opts, _ = get_args()
  return run(opts.type, opts.spec)[0]


if __name__ == '__main__':
  sys.exit(main())
