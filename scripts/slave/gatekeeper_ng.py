#!/usr/bin/env python
# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Closes tree if configured masters have failed tree-closing steps.

Given a list of masters, gatekeeper_ng will get a list of the latest builds from
the specified masters. It then checks if any tree-closing steps have failed, and
if so closes the tree and emails appropriate parties. Configuration for which
steps to close and which parties to notify are in a local gatekeeper.json file.
"""

from contextlib import closing, contextmanager
import getpass
import hashlib
import hmac
import itertools
import json
import logging
import operator
import optparse
import os
import random
import re
import sys
import time
import urllib
import urllib2

from common import chromium_utils
from slave import gatekeeper_ng_config
from slave import gatekeeper_ng_db

SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           '..', '..')

# Buildbot status enum.
SUCCESS, WARNINGS, FAILURE, SKIPPED, EXCEPTION, RETRY = range(6)


def get_pwd(password_file):
  if os.path.isfile(password_file):
    return open(password_file, 'r').read().strip()
  return getpass.getpass()


def update_status(tree_message, tree_status_url, username, password):
  """Connects to chromium-status and closes the tree."""
  #TODO(xusydoc): append status if status is already closed.
  params = urllib.urlencode({
      'message': tree_message,
      'username': username,
      'password': password
  })

  # Standard urllib doesn't raise an exception on 403, urllib2 does.
  f = urllib2.urlopen(tree_status_url, params)
  f.close()
  logging.info('success')


def get_root_json(master_url):
  """Pull down root JSON which contains builder and build info."""
  logging.info('opening %s' % (master_url + '/json'))
  with closing(urllib2.urlopen(master_url + '/json')) as f:
    return json.load(f)


def find_new_builds(master_url, root_json, build_db):
  """Given a dict of previously-seen builds, find new builds on each builder.

  Note that we use the 'cachedBuilds' here since it should be faster, and this
  script is meant to be run frequently enough that it shouldn't skip any builds.

  'Frequently enough' means 1 minute in the case of Buildbot or cron, so the
  only way for gatekeeper_ng to be overwhelmed is if > cachedBuilds builds
  complete within 1 minute. As cachedBuilds is scaled per number of slaves per
  builder, the only way for this to really happen is if a build consistently
  takes < 1 minute to complete.
  """
  new_builds = {}
  build_db.masters[master_url] = build_db.masters.get(master_url, {})

  last_finished_build = {}
  for builder, builds in build_db.masters[master_url].iteritems():
    finished = [int(y[0]) for y in filter(
        lambda x: x[1].finished, builds.iteritems())]
    if finished:
      last_finished_build[builder] = max(finished)

  for buildername, builder in root_json['builders'].iteritems():
    # cachedBuilds are the builds in the cache, while currentBuilds are the
    # currently running builds. Thus cachedBuilds can be unfinished or finished,
    # while currentBuilds are always unfinished.
    candidate_builds = set(builder['cachedBuilds'] + builder['currentBuilds'])
    if buildername in last_finished_build:
      new_builds[buildername] = [
          buildnum for buildnum in candidate_builds
          if buildnum > last_finished_build[buildername]]
    else:
      if buildername in build_db.masters[master_url]:
        # We've seen this builder before, but haven't seen a finished build.
        # Scan finished builds as well as unfinished.
        new_builds[buildername] = candidate_builds
      else:
        # We've never seen this builder before, only scan unfinished builds.

        # We're explicitly only dealing with current builds since we haven't
        # seen this builder before. Thus, the next time gatekeeper_ng is run,
        # only unfinished builds will be in the build_db. This immediately drops
        # us into the section above (builder is in the db, but no finished
        # builds yet.) In this state all the finished builds will be loaded in,
        # firing off an email storm any time the build_db changes or a new
        # builder is added. We set the last finished build here to prevent that.
        if builder['cachedBuilds']:
          max_build = max(builder['cachedBuilds'])
          build_db.masters[master_url].setdefault(buildername, {})[
              max_build] = gatekeeper_ng_db.gen_build(finished=True)

        new_builds[buildername] = builder['currentBuilds']

  return new_builds


def find_new_builds_per_master(masters, build_db):
  """Given a list of masters, find new builds and collect them under a dict."""
  builds = {}
  master_jsons = {}
  for master in masters:
    root_json = get_root_json(master)
    master_jsons[master] = root_json
    builds[master] = find_new_builds(master, root_json, build_db)
  return builds, master_jsons


def get_build_json(url_tuple):
  """Downloads the json of a specific build."""
  url, master, builder, buildnum = url_tuple
  logging.debug('opening %s...' % url)
  with closing(urllib2.urlopen(url)) as f:
    return json.load(f), master, builder, buildnum


def get_build_jsons(master_builds, processes):
  """Get all new builds on specified masters.

  This takes a dict in the form of [master][builder][build], formats that URL
  and appends that to url_list. Then, it forks out and queries each build_url
  for build information.
  """
  url_list = []
  for master, builder_dict in master_builds.iteritems():
    for builder, new_builds in builder_dict.iteritems():
      for buildnum in new_builds:
        safe_builder = urllib.quote(builder)
        url = master + '/json/builders/%s/builds/%s' % (safe_builder,
                                                        buildnum)
        url_list.append((url, master, builder, buildnum))

  # Prevent map from hanging, see http://bugs.python.org/issue12157.
  if url_list:
    # The async/get is so that ctrl-c can interrupt the scans.
    # See http://stackoverflow.com/questions/1408356/
    # keyboard-interrupts-with-pythons-multiprocessing-pool
    with chromium_utils.MultiPool(processes) as pool:
      builds = filter(bool, pool.map_async(get_build_json, url_list).get(
          9999999))
  else:
    builds = []

  return builds


def propagate_build_json_to_db(build_db, builds):
  """Propagates build status changes from build_json to build_db."""
  for build_json, master, builder, buildnum in builds:
    build = build_db.masters[master].setdefault(builder, {}).get(buildnum)
    if not build:
      build = gatekeeper_ng_db.gen_build()

    if build_json.get('results', None) is not None:
      build = build._replace(finished=True)  # pylint: disable=W0212

    build_db.masters[master][builder][buildnum] = build


def check_builds(master_builds, master_jsons, gatekeeper_config):
  """Given a gatekeeper configuration, see which builds have failed."""
  failed_builds = []
  for build_json, master_url, builder, buildnum in master_builds:
    gatekeeper_sections = gatekeeper_config.get(master_url, [])
    for gatekeeper_section in gatekeeper_sections:
      section_hash = gatekeeper_ng_config.gatekeeper_section_hash(
          gatekeeper_section)

      if build_json['builderName'] in gatekeeper_section:
        gatekeeper = gatekeeper_section[build_json['builderName']]
      elif '*' in gatekeeper_section:
        gatekeeper = gatekeeper_section['*']
      else:
        gatekeeper = {}

      steps = build_json['steps']
      forgiving = set(gatekeeper.get('forgiving_steps', []))
      forgiving_optional = set(gatekeeper.get('forgiving_optional', []))
      closing_steps = set(gatekeeper.get('closing_steps', [])) | forgiving
      closing_optional = set(
          gatekeeper.get('closing_optional', [])) | forgiving_optional
      tree_notify = set(gatekeeper.get('tree_notify', []))
      sheriff_classes = set(gatekeeper.get('sheriff_classes', []))
      subject_template = gatekeeper.get('subject_template',
                                        gatekeeper_ng_config.DEFAULTS[
                                            'subject_template'])
      finished = [s for s in steps if s.get('isFinished')]
      close_tree = gatekeeper.get('close_tree', True)
      respect_build_status = gatekeeper.get('respect_build_status', False)

      successful_steps = set(s['name'] for s in finished
                             if (s.get('results', [FAILURE])[0] == SUCCESS or
                                 s.get('results', [FAILURE])[0] == WARNINGS))

      finished_steps = set(s['name'] for s in finished)

      if '*' in forgiving_optional:
        forgiving_optional = finished_steps
      if '*' in closing_optional:
        closing_optional = finished_steps

      unsatisfied_steps = closing_steps - successful_steps
      failed_steps = finished_steps - successful_steps
      failed_optional_steps = failed_steps & closing_optional
      unsatisfied_steps |= failed_optional_steps

      # Build is not yet finished, don't penalize on unstarted/unfinished steps.
      if build_json.get('results', None) is None:
        unsatisfied_steps &= finished_steps

      # If the entire build failed.
      if (not unsatisfied_steps and 'results' in build_json and
          build_json['results'] != SUCCESS and respect_build_status):
        unsatisfied_steps.add('[overall build status]')

      buildbot_url = master_jsons[master_url]['project']['buildbotURL']
      project_name = master_jsons[master_url]['project']['title']

      if unsatisfied_steps:
        failed_builds.append(({'base_url': buildbot_url,
                               'build': build_json,
                               'close_tree': close_tree,
                               'forgiving_steps': (
                                   forgiving | forgiving_optional),
                               'project_name': project_name,
                               'sheriff_classes': sheriff_classes,
                               'subject_template': subject_template,
                               'tree_notify': tree_notify,
                               'unsatisfied': unsatisfied_steps,
                              },
                              master_url,
                              builder,
                              buildnum,
                              section_hash))

  return failed_builds


def debounce_failures(failed_builds, build_db):
  """Using trigger information in build_db, make sure we don't double-fire."""

  @contextmanager
  def log_section(url, builder, buildnum, section_hash):
    """Wraps each build with a log."""
    logging.debug('%sbuilders/%s/builds/%d ----', url, builder, buildnum)
    logging.debug('  section hash: %s', section_hash)
    yield
    logging.debug('----')

  @contextmanager
  def save_build_failures(master_url, builder, buildnum, section_hash,
                          unsatisfied):
    yield
    build_db.masters[master_url][builder][buildnum].triggered[
        section_hash] = unsatisfied

  true_failed_builds = []
  for build, master_url, builder, buildnum, section_hash in failed_builds:
    with log_section(build['base_url'], builder, buildnum, section_hash):
      with save_build_failures(master_url, builder, buildnum, section_hash,
                               build['unsatisfied']):
        build_db_builder = build_db.masters[master_url][builder]

        # Determine what the current and previous failing steps are.
        prev_triggered = []
        if buildnum-1 in build_db_builder:
          prev_triggered = build_db_builder[buildnum-1].triggered.get(
              section_hash, [])

        logging.debug('  previous failing tests: %s', ','.join(
            sorted(prev_triggered)))
        logging.debug('  current failing tests: %s', ','.join(
            sorted(build['unsatisfied'])))

        # Skip build if we already fired (or if the failing tests aren't new).
        if section_hash in build_db_builder[buildnum].triggered:
          logging.debug('  section has already been triggered for this build, '
                        'skipping...')
          continue

        new_tests = set(build['unsatisfied']) - set(prev_triggered)
        if not new_tests:
          logging.debug('  no new steps failed since previous build %d',
                        buildnum-1)
          continue

        logging.debug('  new failing steps since build %d: %s', buildnum-1,
                      ','.join(sorted(new_tests)))

        # If we're here it's a legit failing build.
        true_failed_builds.append(build)

        logging.debug('  build steps: %s', ', '.join(
            s['name'] for s in build['build']['steps']))
        logging.debug('  build complete: %s', bool(
            build['build'].get('results', None) is not None))
        logging.debug('  set to close tree: %s', build['close_tree'])
        logging.debug('  build failed: %s', bool(build['unsatisfied']))

  return true_failed_builds


def parse_sheriff_file(url):
  """Given a sheriff url, download and parse the appropirate sheriff list."""
  with closing(urllib2.urlopen(url)) as f:
    line = f.readline()
  usernames_matcher_ = re.compile(r'document.write\(\'([\w, ]+)\'\)')
  usernames_match = usernames_matcher_.match(line)
  sheriffs = set()
  if usernames_match:
    usernames_str = usernames_match.group(1)
    if usernames_str != 'None (channel is sheriff)':
      for sheriff in usernames_str.split(', '):
        if sheriff.count('@') == 0:
          sheriff += '@google.com'
        sheriffs.add(sheriff)
  return sheriffs


def get_sheriffs(classes, base_url):
  """Given a list of sheriff classes, download and combine sheriff emails."""
  sheriff_sets = (parse_sheriff_file(base_url % cls) for cls in classes)
  return reduce(operator.or_, sheriff_sets, set())


def hash_message(message, url, secret):
  utc_now = time.time()
  salt = random.getrandbits(32)
  hasher = hmac.new(secret, message, hashlib.sha256)
  hasher.update(str(utc_now))
  hasher.update(str(salt))
  client_hash = hasher.hexdigest()

  return {'message': message,
          'time': utc_now,
          'salt': salt,
          'url': url,
          'hmac-sha256': client_hash,
         }


def submit_email(email_app, build_data, secret):
  """Submit json to a mailer app which sends out the alert email."""

  url = email_app + '/email'
  data = hash_message(json.dumps(build_data, sort_keys=True), url, secret)

  req = urllib2.Request(url, urllib.urlencode({'json': json.dumps(data)}))
  with closing(urllib2.urlopen(req)) as f:
    code = f.getcode()
    if code != 200:
      response = f.read()
      raise Exception('error connecting to email app: code %d %s' % (
          code, response))


def close_tree_if_failure(failed_builds, username, password, tree_status_url,
                          set_status, sheriff_url, default_from_email,
                          email_app_url, secret, domain, filter_domain,
                          disable_domain_filter):
  """Given a list of failed builds, close the tree and email tree watchers."""
  if not failed_builds:
    logging.info( 'no failed builds!')
    return

  logging.info('%d failed builds found, closing the tree...' %
               len(failed_builds))
  closing_builds = [b for b in failed_builds if b['close_tree']]
  if closing_builds:
    # Close on first failure seen.
    msg = 'Tree is closed (Automatic: "%(steps)s" on "%(builder)s" %(blame)s)'
    tree_status = msg % {'steps': ','.join(closing_builds[0]['unsatisfied']),
                         'builder': failed_builds[0]['build']['builderName'],
                         'blame':
                         ','.join(failed_builds[0]['build']['blame'])
                        }

    logging.info('closing the tree with message: \'%s\'' % tree_status)
    if set_status:
      update_status(tree_status, tree_status_url, username, password)
    else:
      logging.info('set-status not set, not connecting to chromium-status!')
  # Email everyone that should be notified.
  emails_to_send = []
  for failed_build in failed_builds:
    waterfall_url = failed_build['base_url'].rstrip('/')
    build_url = '%s/builders/%s/builds/%d' % (
        failed_build['base_url'].rstrip('/'),
        failed_build['build']['builderName'],
        failed_build['build']['number'])
    project_name = failed_build['project_name']
    fromaddr = failed_build['build'].get('fromAddr', default_from_email)

    tree_notify = failed_build['tree_notify']

    if failed_build['unsatisfied'] <= failed_build['forgiving_steps']:
      blamelist = set()
    else:
      blamelist = set(failed_build['build']['blame'])

    sheriffs = get_sheriffs(failed_build['sheriff_classes'], sheriff_url)
    watchers = list(tree_notify | blamelist | sheriffs)

    build_data = {
        'build_url': build_url,
        'from_addr': fromaddr,
        'project_name': project_name,
        'subject_template': failed_build['subject_template'],
        'steps': [],
        'unsatisfied': list(failed_build['unsatisfied']),
        'waterfall_url': waterfall_url,
    }

    for field in ['builderName', 'number', 'reason']:
      build_data[field] = failed_build['build'][field]

    build_data['result'] = failed_build['build'].get('results', 0)
    build_data['blamelist'] = failed_build['build']['blame']
    build_data['changes'] = failed_build['build'].get('sourceStamp', {}).get(
        'changes', [])

    build_data['revisions'] = [x['revision'] for x in build_data['changes']]

    for step in failed_build['build']['steps']:
      new_step = {}
      for field in ['text', 'name', 'logs']:
        new_step[field] = step[field]
      new_step['started'] = step.get('isStarted', False)
      new_step['urls'] = step.get('urls', [])
      new_step['results'] = step.get('results', [0, None])[0]
      build_data['steps'].append(new_step)

    if email_app_url and watchers:
      emails_to_send.append((watchers, json.dumps(build_data, sort_keys=True)))

    buildnum = failed_build['build']['number']
    steps = failed_build['unsatisfied']
    builder = failed_build['build']['builderName']
    logging.info(
        'to %s: failure in %s build %s: %s' % (', '.join(watchers),
                                                        builder, buildnum,
                                                        list(steps)))
    if not email_app_url:
      logging.warn('no email_app_url specified, no email sent!')

  filtered_emails_to_send = []
  for email in emails_to_send:
    new_watchers  = [x if '@' in x else (x + '@' + domain) for x in email[0]]
    if not disable_domain_filter:
      new_watchers = [x for x in new_watchers if x.split('@')[-1] in
                      filter_domain]
    if new_watchers:
      filtered_emails_to_send.append((new_watchers, email[1]))

  # Deduplicate emails.
  keyfunc = lambda x: x[1]
  for k, g in itertools.groupby(sorted(filtered_emails_to_send, key=keyfunc),
                                keyfunc):
    watchers = list(reduce(operator.or_, [set(e[0]) for e in g], set()))
    build_data = json.loads(k)
    build_data['recipients'] = watchers
    submit_email(email_app_url, build_data, secret)


def get_options():
  prog_desc = 'Closes the tree if annotated builds fail.'
  usage = '%prog [options] <one or more master urls>'
  parser = optparse.OptionParser(usage=(usage + '\n\n' + prog_desc))
  parser.add_option('--build-db', default='build_db.json',
                    help='records the last-seen build for each builder')
  parser.add_option('--clear-build-db', action='store_true',
                    help='reset build_db to be empty')
  parser.add_option('--sync-build-db', action='store_true',
                    help='don\'t process any builds, but update build_db '
                         'to the latest build numbers')
  parser.add_option('--skip-build-db-update', action='store_true',
                    help='don\' write to the build_db, overridden by sync and'
                         ' clear db options')
  parser.add_option('--password-file', default='.status_password',
                    help='password file to update chromium-status')
  parser.add_option('-s', '--set-status', action='store_true',
                    help='close the tree by connecting to chromium-status')
  parser.add_option('--status-url',
                    default='https://chromium-status.appspot.com/status',
                    help='URL for the status app')
  parser.add_option('--status-user', default='buildbot@chromium.org',
                    help='username for the status app')
  parser.add_option('--disable-domain-filter', action='store_true',
                    help='allow emailing any domain')
  parser.add_option('--filter-domain', default='chromium.org,google.com',
                    help='only email users in these comma separated domains')
  parser.add_option('--email-domain', default='google.com',
                    help='default email domain to add to users without one')
  parser.add_option('--sheriff-url',
                    default='http://build.chromium.org/p/chromium/%s.js',
                    help='URL pattern for the current sheriff list')
  parser.add_option('--parallelism', default=16,
                    help='up to this many builds can be queried simultaneously')
  parser.add_option('--default-from-email',
                    default='buildbot@chromium.org',
                    help='default email address to send from')
  parser.add_option('--email-app-url',
                    default='https://chromium-build.appspot.com/mailer',
                    help='URL of the application to send email from')
  parser.add_option('--email-app-secret-file',
                    default='.gatekeeper_secret',
                    help='file containing secret used in email app auth')
  parser.add_option('--no-email-app', action='store_true',
                    help='don\'t send emails')
  parser.add_option('--json', default='gatekeeper.json',
                    help='location of gatekeeper configuration file')
  parser.add_option('--verify', action='store_true',
                    help='verify that the gatekeeper config file is correct')
  parser.add_option('--flatten-json', action='store_true',
                    help='display flattened gatekeeper.json for debugging')
  parser.add_option('--no-hashes', action='store_true',
                    help='don\'t insert gatekeeper section hashes')
  parser.add_option('-v', '--verbose', action='store_true',
                    help='turn on extra debugging information')

  options, args = parser.parse_args()

  options.email_app_secret = None
  options.password = None

  if options.no_hashes and not options.flatten_json:
    parser.error('specifying --no-hashes doesn\'t make sense without '
                 '--flatten-json')

  if options.verify or options.flatten_json:
    return options, args

  if not args:
    parser.error('you need to specify at least one master URL')

  if options.no_email_app:
    options.email_app_url = None

  if options.email_app_url:
    if os.path.exists(options.email_app_secret_file):
      with open(options.email_app_secret_file) as f:
        options.email_app_secret = f.read().strip()
    else:
      parser.error('Must provide email app auth with  %s.' % (
          options.email_app_secret_file))

  options.filter_domain = options.filter_domain.split(',')

  args = [url.rstrip('/') for url in args]

  return options, args


def main():
  options, args = get_options()

  logging.basicConfig(level=logging.DEBUG if options.verbose else logging.INFO)

  gatekeeper_config = gatekeeper_ng_config.load_gatekeeper_config(options.json)

  if options.verify:
    return 0

  if options.flatten_json:
    if not options.no_hashes:
      gatekeeper_config = gatekeeper_ng_config.inject_hashes(gatekeeper_config)
    gatekeeper_ng_config.flatten_to_json(gatekeeper_config, sys.stdout)
    print
    return 0

  if options.set_status:
    options.password = get_pwd(options.password_file)

  masters = set(args)
  if not masters <= set(gatekeeper_config):
    print 'The following masters are not present in the gatekeeper config:'
    for m in masters - set(gatekeeper_config):
      print '  ' + m
    return 1

  if options.clear_build_db:
    build_db = {}
    gatekeeper_ng_db.save_build_db(build_db, gatekeeper_config,
                                   options.build_db)
  else:
    build_db = gatekeeper_ng_db.get_build_db(options.build_db)

  new_builds, master_jsons = find_new_builds_per_master(masters, build_db)
  build_jsons = get_build_jsons(new_builds, options.parallelism)
  propagate_build_json_to_db(build_db, build_jsons)

  if options.sync_build_db:
    gatekeeper_ng_db.save_build_db(build_db, gatekeeper_config,
                                   options.build_db)
    return 0

  failed_builds = check_builds(build_jsons, master_jsons, gatekeeper_config)
  failed_builds = debounce_failures(failed_builds, build_db)

  close_tree_if_failure(failed_builds, options.status_user, options.password,
                        options.status_url, options.set_status,
                        options.sheriff_url, options.default_from_email,
                        options.email_app_url, options.email_app_secret,
                        options.email_domain, options.filter_domain,
                        options.disable_domain_filter)

  if not options.skip_build_db_update:
    gatekeeper_ng_db.save_build_db(build_db, gatekeeper_config,
                                   options.build_db)

  return 0


if __name__ == '__main__':
  sys.exit(main())
