# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import re

import buildbot
from buildbot import interfaces, util
from buildbot.buildsubordinate import BuildSubordinate
from buildbot.interfaces import IRenderable
from buildbot.status import mail
from buildbot.status.builder import BuildStatus
from buildbot.status.status_push import HttpStatusPush
from twisted.python import log
from zope.interface import implements

from main.autoreboot_buildsubordinate import AutoRebootBuildSubordinate
from buildbot.status.web.authz import Authz
from buildbot.status.web.baseweb import WebStatus
from buildbot.status.web.baseweb import WebStatus

import main.chromium_status_bb8 as chromium_status

from common import chromium_utils
from main import status_logger
import config


def HackMaxTime(maxTime=8*60*60):
  """Set maxTime default value to 8 hours. This function must be called before
  adding steps."""
  from buildbot.process.buildstep import RemoteShellCommand
  assert RemoteShellCommand.__init__.func_defaults == (None, 1, 1, 1200, None,
      {}, 'subordinate-config', True)
  RemoteShellCommand.__init__.im_func.func_defaults = (None, 1, 1, 1200,
      maxTime, {}, 'subordinate-config', True)
  assert RemoteShellCommand.__init__.func_defaults == (None, 1, 1, 1200,
      maxTime, {}, 'subordinate-config', True)

HackMaxTime()


def HackBuildStatus():
  """Adds a property to Build named 'blamelist' with the blamelist."""
  old_setBlamelist = BuildStatus.setBlamelist
  def setBlamelist(self, blamelist):
    self.setProperty('blamelist', blamelist, 'Build')
    old_setBlamelist(self, blamelist)
  BuildStatus.setBlamelist = setBlamelist

HackBuildStatus()


class InvalidConfig(Exception):
  """Used by VerifySetup."""
  pass


def AutoSetupSubordinates(builders, bot_password, max_builds=1,
                    missing_recipients=None, missing_timeout=300):
  """Helper function for main.cfg to quickly setup c['subordinates']."""
  subordinates_dict = {}
  for builder in builders:
    auto_reboot = builder.get('auto_reboot', True)
    notify_on_missing = builder.get('notify_on_missing', False)
    subordinatenames = builder.get('subordinatenames', [])[:]
    if 'subordinatename' in builder:
      subordinatenames.append(builder['subordinatename'])
    for subordinatename in subordinatenames:
      subordinates_dict[subordinatename] = (auto_reboot, notify_on_missing)
  subordinates = []
  for (subordinatename, (auto_reboot, notify_on_missing)) in subordinates_dict.iteritems():
    if auto_reboot:
      subordinate_class = AutoRebootBuildSubordinate
    else:
      subordinate_class = BuildSubordinate

    if notify_on_missing:
      subordinates.append(subordinate_class(subordinatename, bot_password, max_builds=max_builds,
                                notify_on_missing=missing_recipients,
                                missing_timeout=missing_timeout))
    else:
      subordinates.append(subordinate_class(subordinatename, bot_password, max_builds=max_builds))
  return subordinates


def VerifySetup(c, subordinates):
  """Verify all the available subordinates in the subordinate configuration are used and
  that all the builders have a subordinate."""
  # Extract the list of subordinates associated to a builder and make sure each
  # builder has its subordinates connected.
  # Verify each builder has at least one subordinate.
  builders_subordinates = set()
  subordinates_name = [s.subordinatename for s in c['subordinates']]
  for b in c['builders']:
    builder_subordinates = set()
    subordinatename = b.get('subordinatename')
    if subordinatename:
      builder_subordinates.add(subordinatename)
    subordinatenames = b.get('subordinatenames', [])
    for s in subordinatenames:
      builder_subordinates.add(s)
    if not subordinatename and not subordinatenames:
      raise InvalidConfig('Builder %s has no subordinate' % b['name'])
    # Now test.
    for s in builder_subordinates:
      if not s in subordinates_name:
        raise InvalidConfig('Builder %s using undefined subordinate %s' % (b['name'],
                                                                     s))
    builders_subordinates |= builder_subordinates
  if len(builders_subordinates) != len(subordinates_name):
    raise InvalidConfig('Same subordinate defined multiple times')

  # Make sure each subordinate has their builder.
  builders_name = [b['name'] for b in c['builders']]
  for s in c['subordinates']:
    name = s.subordinatename
    if not name in builders_subordinates:
      raise InvalidConfig('Subordinate %s not associated with any builder' % name)

  # Make sure every defined subordinate is used.
  for s in subordinates.GetSubordinates():
    name = chromium_utils.EntryToSubordinateName(s)
    if not name in subordinates_name:
      raise InvalidConfig('Subordinate %s defined in your subordinates_list is not '
                          'referenced at all' % name)
    builders = s.get('builder', [])
    if not isinstance(builders, (list, tuple)):
      builders = [builders]
    testers = s.get('testers', [])
    if not isinstance(testers, (list, tuple)):
      testers = [testers]
    builders.extend(testers)
    for b in builders:
      if not b in builders_name:
        raise InvalidConfig('Subordinate %s uses non-existent builder %s' % (name,
                                                                       b))

class UsersAreEmails(util.ComparableMixin):
  """Chromium already uses email addresses as user name so no need to do
  anything.
  """
  # Class has no __init__ method
  # pylint: disable=W0232
  implements(interfaces.IEmailLookup)

  @staticmethod
  def getAddress(name):
    return name


class FilterDomain(util.ComparableMixin):
  """Similar to buildbot.mail.Domain but permits filtering out people we don't
  want to spam.

  Also loads default values from chromium_config."""
  implements(interfaces.IEmailLookup)

  compare_attrs = ['domain', 'permitted_domains']


  def __init__(self, domain=None, permitted_domains=None):
    """domain is the default domain to append when only the naked username is
    available.
    permitted_domains is a whitelist of domains that emails will be sent to."""
    # pylint: disable=E1101
    self.domain = domain or config.Main.main_domain
    self.permitted_domains = (permitted_domains or
                              config.Main.permitted_domains)

  def getAddress(self, name):
    """If name is already an email address, pass it through."""
    result = name
    if self.domain and not '@' in result:
      result = '%s@%s' % (name, self.domain)
    if not '@' in result:
      log.msg('Invalid blame email address "%s"' % result)
      return None
    if self.permitted_domains:
      for p in self.permitted_domains:
        if result.endswith(p):
          return result
      return None
    return result


def CreateWebStatus(port, templates=None, tagComparator=None,
                    customEndpoints=None, console_repo_filter=None,
                    console_builder_filter=None, **kwargs):
  webstatus = WebStatus(port, **kwargs)
  if templates:
    # Manipulate the search path for jinja templates
    # pylint: disable=F0401
    import jinja2
    # pylint: disable=E1101
    old_loaders = webstatus.templates.loader.loaders
    # pylint: disable=E1101
    new_loaders = old_loaders[:1]
    new_loaders.extend([jinja2.FileSystemLoader(x) for x in templates])
    new_loaders.extend(old_loaders[1:])
    webstatus.templates.loader.loaders = new_loaders
  chromium_status.SetupChromiumPages(
      webstatus, tagComparator, customEndpoints,
      console_repo_filter=console_repo_filter,
      console_builder_filter=console_builder_filter)
  return webstatus


def GetMainname():
  # Get the main name from the directory name. Remove leading "main.".
  return re.sub('^main.', '', os.path.basename(os.getcwd()))


def AutoSetupMain(c, active_main, mail_notifier=False,
                    mail_notifier_mode=None,
                    public_html=None, templates=None,
                    order_console_by_time=False,
                    tagComparator=None,
                    customEndpoints=None,
                    enable_http_status_push=False,
                    console_repo_filter=None,
                    console_builder_filter=None):
  """Add common settings and status services to a main.

  If you wonder what all these mean, PLEASE go check the official doc!
  http://buildbot.net/buildbot/docs/0.7.12/ or
  http://buildbot.net/buildbot/docs/latest/full.html

  - Default number of logs to keep
  - WebStatus and MailNotifier
  - Debug ssh port. Just add a file named .manhole beside main.cfg and
    simply include one line containing 'port = 10101', then you can
    'ssh localhost -p' and you can access your buildbot from the inside."""
  c['subordinatePortnum'] = active_main.subordinate_port
  c['projectName'] = active_main.project_name
  c['projectURL'] = config.Main.project_url

  c['properties'] = {'mainname': GetMainname()}
  if 'buildbotURL' in c:
    c['properties']['buildbotURL'] = c['buildbotURL']

  # 'status' is a list of Status Targets. The results of each build will be
  # pushed to these targets. buildbot/status/*.py has a variety to choose from,
  # including web pages, email senders, and IRC bots.
  c.setdefault('status', [])
  if mail_notifier:
    # pylint: disable=E1101
    c['status'].append(mail.MailNotifier(
        fromaddr=active_main.from_address,
        mode=mail_notifier_mode or 'problem',
        relayhost=config.Main.smtp,
        lookup=FilterDomain()))

  # For all production mains, notify our health-monitoring webapp.
  if enable_http_status_push:
    blacklist = (
        'buildETAUpdate',
        #'buildFinished',
        'buildStarted',
        'buildedRemoved',
        'builderAdded',
        'builderChangedState',
        'buildsetSubmitted',
        'changeAdded',
        'logFinished',
        'logStarted',
        'requestCancelled',
        'requestSubmitted',
        'subordinateConnected',
        'subordinateDisconnected',
        'stepETAUpdate',
        'stepFinished',
        'stepStarted',
        'stepText2Changed',
        'stepTextChanged',
    )
    c['status'].append(HttpStatusPush(
        'https://chromium-build-logs.appspot.com/status_receiver',
        blackList=blacklist))

  kwargs = {}
  if public_html:
    kwargs['public_html'] = public_html
  kwargs['order_console_by_time'] = order_console_by_time
  # In Buildbot 0.8.4p1, pass provide_feeds as a list to signal what extra
  # services Buildbot should be able to provide over HTTP.
  if buildbot.version == '0.8.4p1':
    kwargs['provide_feeds'] = ['json']
  if active_main.main_port:
    # Actions we want to allow must be explicitly listed here.
    # Deliberately omitted are:
    #   - gracefulShutdown
    #   - cleanShutdown
    authz = Authz(forceBuild=True,
                  forceAllBuilds=True,
                  pingBuilder=True,
                  stopBuild=True,
                  stopAllBuilds=True,
                  cancelPendingBuild=True)
    c['status'].append(CreateWebStatus(
        active_main.main_port,
        tagComparator=tagComparator,
        customEndpoints=customEndpoints,
        authz=authz,
        num_events_max=3000,
        templates=templates,
        console_repo_filter=console_repo_filter,
        console_builder_filter=console_builder_filter,
        **kwargs))
  if active_main.main_port_alt:
    c['status'].append(CreateWebStatus(
        active_main.main_port_alt,
        tagComparator=tagComparator,
        customEndpoints=customEndpoints,
        num_events_max=3000,
        templates=templates,
        console_repo_filter=console_repo_filter,
        console_builder_filter=console_builder_filter,
        **kwargs))

  # Add a status logger, which is only active if '.logstatus' is touched.
  c['status'].append(status_logger.StatusEventLogger())

  # Keep last build logs, the default is too low.
  c['buildHorizon'] = 1000
  c['logHorizon'] = 500
  # Must be at least 2x the number of subordinates.
  c['eventHorizon'] = 200
  # Tune cache sizes to speed up web UI.
  c['caches'] = {
    'BuildRequests': 1000,
    'Changes': 1000,
    'SourceStamps': 1000,
    'chdicts': 1000,
    'ssdicts': 1000,
  }
  # Must be at least 2x the number of on-going builds.
  c['buildCacheSize'] = 200

  # See http://buildbot.net/buildbot/docs/0.8.1/Debug-Options.html for more
  # details.
  if os.path.isfile('.manhole'):
    try:
      from buildbot import manhole
    except ImportError:
      log.msg('Using manhole has an implicit dependency on Crypto.Cipher. You '
              'need to install it manually:\n'
              '  sudo apt-get install python-crypto\n'
              'on ubuntu or run:\n'
              '  pip install --user pycrypto\n'
              '  pip install --user pyasn1\n')
      raise

    # If 'port' is defined, it uses the same valid keys as the current user.
    values = {}
    execfile('.manhole', values)
    if 'debugPassword' in values:
      c['debugPassword'] = values['debugPassword']
    interface = 'tcp:%s:interface=127.0.0.1' % values.get('port', 0)
    if 'port' in values and 'user' in values and 'password' in values:
      c['manhole'] = manhole.PasswordManhole(interface, values['user'],
                                            values['password'])
    elif 'port' in values:
      c['manhole'] = manhole.AuthorizedKeysManhole(interface,
          os.path.expanduser("~/.ssh/authorized_keys"))

def DumpSetup(c, important=None, filename='config.current.txt'):
  """Writes a flattened version of the setup to a text file.
     Some interesting classes are exploded with their variables
     exposed,  by default the BuildFactories and Schedulers.
     Newlines and indentation are sprinkled through the representation,
     to make the output more easily broken up and groked with grep or diff.

     Note that the heuristics of how to find classes that you want expanded
     is not too hard to fool, but it seems to handle it usefully for
     normal main configs.

     c         The config: same as the rest of the utilities here.
     important Array of classes to also expand.
     filename  Where to write this ill-defined but useful information.
  """
  from buildbot.schedulers.base import BaseScheduler
  from buildbot.process.factory import BuildFactory

  def hacky_repr(obj, name, indent, important):
    def hacky_repr_class(obj, indent, subdent, important):
      r = '%s {\n' % obj.__class__.__name__
      for (n, v) in vars(obj).iteritems():
        if not n.startswith('_'):
          r += hacky_repr(v, "%s: " % n, indent + subdent, important) + ',\n'
      r += indent + '}'
      return r

    if isinstance(obj, list):
      r = '[' + ', '.join(hacky_repr(o, '', '', important) for o in obj) + ']'
    elif isinstance(obj, tuple):
      r = '(' + ', '.join(hacky_repr(o, '', '', important) for o in obj) + ')'
    else:
      r = repr(obj)
      if not isinstance(obj, basestring):
        r = re.sub(' at 0x[0-9a-fA-F]*>', '>', r)

    subdent = '  '
    if any(isinstance(obj, c) for c in important):
      r = hacky_repr_class(obj, indent, subdent, important)
    elif len(r) > max(30, 76-len(indent)-len(name)) and \
        not isinstance(obj, basestring):
      if isinstance(obj, list):
        r = '[\n'
        for o in obj:
          r += hacky_repr(o, '', indent + subdent, important) + ',\n'
        r += indent + ']'
      elif isinstance(obj, tuple):
        r = '(\n'
        for o in obj:
          r += hacky_repr(o, '', indent + subdent, important) + ',\n'
        r += indent + ')'
      elif isinstance(obj, dict):
        r = '{\n'
        for (n, v) in sorted(obj.iteritems(), key=lambda x: x[0]):
          if not n.startswith('_'):
            r += hacky_repr(v, "'%s': " % n, indent + subdent, important)
            r += ',\n'
        r += indent + '}'
    return "%s%s%s" % (indent, name, r)

  important = (important or []) + [BaseScheduler, BuildFactory]

  with open(filename, 'w') as f:
    print >> f, hacky_repr(c, 'config = ', '', important)


def Partition(item_tuples, num_partitions):
  """Divides |item_tuples| into |num_partitions| separate lists.

  Perfect partitioning is NP hard, this is a "good enough" estimate.

  Args:
    item_tuples: tuple in the format (weight, item_name).
    num_partitions: int number of partitions to generate.

  Returns:
    A list of lists of item_names with as close to equal weight as possible.
  """
  assert num_partitions > 0, 'Must pass a positive number of partitions'
  assert len(item_tuples) >= num_partitions, 'Need more items than partitions'
  partitions = [[] for _ in xrange(num_partitions)]
  def GetLowestSumPartition():
    return sorted(partitions, key=lambda x: sum([i[0] for i in x]))[0]
  for item in sorted(item_tuples, reverse=True):
    GetLowestSumPartition().append(item)
  return sorted([sorted([name for _, name in p]) for p in partitions])


class ConditionalProperty(util.ComparableMixin):
  """A IRenderable that chooses between IRenderable options given a condition.

  A typical 'WithProperties' will be rendered as a string and included as an
  argument. If it's an empty string, it will become a position argment, "".

  This property wraps two IRenderables (which can be 'WithProperties' instances)
  and chooses between them based on a condition. This allows the full exclusion
  and tailoring of property output.

  For example, to optionally add a parameter, one can use the following recipe:
  args.append(
      ConditionalProperty(
          'author_name',
          WithProperties('--author-name=%(author_name)s'),
          [],
      )
  )

  In this example, if 'author_name' is defined as a property, the first
  IRenderable (WithProperties) will be rendered and the '--author-name' argument
  will be inclided. Otherwise, the second will be rendered. Since 'step'
  flattens the command list, returning '[]' will result in the argument being
  completely omitted.

  If a more complex condition is required, a callable function may be used
  as the 'prop' argument. In this case, the function will be passed a single
  parameter, the build object, and is expected to return True if the 'present'
  IRenderable should be used and 'False' if the 'absent' one should be used.
  """
  implements(IRenderable)
  compare_attrs = ('prop', 'present', 'absent')

  def __init__(self, condition, present, absent):
    if not callable(condition):
      self.prop = condition
      condition = lambda build: (self.prop in build.getProperties())
    else:
      self.prop = None
    self.condition = condition
    self.present = present
    self.absent = absent

  def getRenderingFor(self, build):
    # Test whether we're going to render
    is_present = self.condition(build)

    # Choose our inner IRenderer and render it
    renderer = (self.present) if is_present else (self.absent)
    # Disable 'too many positional arguments' error | pylint: disable=E1121
    return IRenderable(renderer).getRenderingFor(build)
