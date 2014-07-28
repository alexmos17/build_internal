# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


"""Classes for polling a git repository via the gitiles web interface.

The advantage of using gitiles is that a local clone is not needed."""

import datetime
import os
import re
import time
import traceback
import urllib
from urlparse import urlparse

import sqlalchemy as sa
from buildbot.status.web.console import RevisionComparator
from buildbot.changes.base import PollingChangeSource
from twisted.internet import defer
from twisted.python import log

from common.gerrit_agent import GerritAgent


LOG_TEMPLATE = '%s/+log/%s?format=JSON&n=%d'
REVISION_DETAIL_TEMPLATE = '%s/+/%s?format=JSON'


def _always_unlock(result, lock):
  lock.release()
  return result

def time_to_datetime(tm):
  return datetime.datetime.strptime(
      tm.partition('+')[0].strip(), "%a %b %d %H:%M:%S %Y")

class GitilesRevisionComparator(RevisionComparator):
  """Tracks the commit order of tags in a git repository."""

  def __init__(self):
    super(GitilesRevisionComparator, self).__init__()
    self.sha1_lookup = {}
    self.initialized = False

  def addRevision(self, revision):
    if revision in self.sha1_lookup:
      return
    idx = len(self.sha1_lookup)
    self.sha1_lookup[revision] = idx

  def tagcmp(self, x, y):
    return cmp(self.sha1_lookup[x], self.sha1_lookup[y])

  def isValidRevision(self, revision):
    return revision in self.sha1_lookup

  def isRevisionEarlier(self, first_change, second_change):
    return self.tagcmp(first_change, second_change) < 0

  def getSortingKey(self):
    return lambda c: self.sha1_lookup.__getitem__(c.revision)


class GitilesPoller(PollingChangeSource):
  """Polls a git repository using the gitiles web interface. """

  git_svn_id_re = re.compile('^git-svn-id: (.*)@([0-9]+) [0-9a-fA-F\-]*$')

  def __init__(
      self, repo_url, branches=None, pollInterval=10*60, category=None,
      project=None, revlinktmpl=None, agent=None, svn_mode=False):
    """Args:

    repo_url: URL of the gitiles service to be polled.
    branches: List of repository branches to be polled.
    pollInterval: Number of seconds between polling operations.
    category: Category to be applied to generated Change objects.
    project: Project to be applied to generated Change objects.
    revlinktmpl: String template, taking a single 'revision' parameter, used to
        generate a web link to a revision.
    agent: A GerritAgent object used to make requests to the gitiles service.
    svn_mode: When polling a mirror of an svn repository, create changes using
        the svn revision number.
    """
    u = urlparse(repo_url)
    self.repo_url = repo_url
    self.repo_host = u.netloc
    self.repo_path = urllib.quote(u.path)
    if branches is None:
      branches = ['master']
    elif isinstance(branches, basestring):
      branches = [branches]
    self.branches = dict([(b, None) for b in branches])
    self.pollInterval = pollInterval
    self.category = category
    if project is None:
      project = os.path.basename(repo_url)
      if project.endswith('.git'):
        project = project[:-4]
    self.project = project
    self.revlinktmpl = revlinktmpl
    self.svn_mode = svn_mode
    if agent is None:
      agent = GerritAgent('%s://%s' % (u.scheme, u.netloc), read_only=True)
    self.agent = agent
    self.comparator = GitilesRevisionComparator()

  @defer.inlineCallbacks
  def startService(self):
    # Initialize revision comparator with revisions from all changes
    # known to buildbot.
    def db_thread_main(conn):
      changes_tbl = self.master.db.model.changes
      q = changes_tbl.select(order_by=[sa.asc(changes_tbl.c.changeid)])
      rp = conn.execute(q)
      for row in rp:
        self.comparator.addRevision(row.revision)
    yield self.master.db.pool.do(db_thread_main)

    # It's now safe to produce the console view.
    self.comparator.initialized = True

    # Get the head commit for each branch being polled.
    for branch in self.branches:
      path = LOG_TEMPLATE % (self.repo_path, branch, 1)
      log_json = yield self.agent.request('GET', path, retry=5)
      assert log_json.get('log'), log_json
      revision = log_json['log'][0]['commit']
      log.msg('GitilesPoller: Initial revision for branch %s is %s' % (
          branch, revision))
      self.branches[branch] = revision

    log.msg('GitilesPoller: Finished initializing revision history')
    PollingChangeSource.startService(self)

  def _create_change(self, commit_json, branch):
    """Send a new Change object to the buildbot master."""
    if not commit_json:
      return
    commit_author = commit_json['author']['email']
    commit_tm = time_to_datetime(commit_json['committer']['time'])
    commit_files = []
    if 'tree_diff' in commit_json:
      commit_files = [
          x['new_path'] for x in commit_json['tree_diff'] if 'new_path' in x]
    commit_msg = commit_json['message']
    repo_url = self.repo_url
    revision = commit_json['commit']
    if self.svn_mode:
      revision = None
      for line in reversed(commit_msg.splitlines()):
        m = self.git_svn_id_re.match(line)
        if m:
          repo_url = m.group(1)
          revision = m.group(2)
          branch = self.project
          break
      if revision is None:
        log.err(
            'GitilesPoller: Could not parse svn revision out of commit message '
            'for commit %s in %s' % (commit_json['commit'], self.repo_url))
        return None
      self.comparator.addRevision(revision)
    revlink = ''
    if self.revlinktmpl and revision:
      revlink = self.revlinktmpl % revision
    return self.master.addChange(
        author=commit_author,
        revision=revision,
        files=commit_files,
        comments=commit_msg,
        when_timestamp=commit_tm,
        branch=branch,
        category=self.category,
        project=self.project,
        repository=repo_url,
        revlink=revlink)

  @defer.inlineCallbacks
  def _fetch_new_commits(self, branch, since):
    """Query gitiles for all commits on 'branch' more recent than 'since'."""
    result = []
    log_json = {'next': branch}
    while 'next' in log_json:
      log_spec = '%s..%s' % (since, log_json['next'])
      path = LOG_TEMPLATE % (self.repo_path, log_spec, 100)
      log_json = yield self.agent.request('GET', path, retry=5)
      if log_json.get('log'):
        result.extend(log_json['log'])
    result.reverse()
    defer.returnValue(result)

  @staticmethod
  def _collate_commits(a, b):
    """Shuffle together two lists of commits.

    The result will be sorted by commit time, while guaranteeing that there are
    no inversions compared to the argument lists."""
    a = [(c, time.mktime(time.strptime(c[0]['committer']['time']))) for c in a]
    b = [(c, time.mktime(time.strptime(c[0]['committer']['time']))) for c in b]
    result = []
    while a and b:
      if a[-1][1] > b[-1][1]:
        result.append(a.pop()[0])
      else:
        result.append(b.pop()[0])
    while a:
      result.append(a.pop()[0])
    while b:
      result.append(b.pop()[0])
    result.reverse()
    return result

  @defer.inlineCallbacks
  def poll(self):
    all_commits = []
    for branch, last_head in self.branches.iteritems():
      try:
        branch_commits = yield self._fetch_new_commits(
            branch, last_head)
        if branch_commits:
          self.branches[branch] = branch_commits[-1]['commit']
          branch_commits = [(c, branch) for c in branch_commits]
          all_commits = self._collate_commits(all_commits, branch_commits)
      except Exception:
        msg = ('GitilesPoller: Error while fetching logs for branch %s:\n%s' %
                   (branch, traceback.format_exc()))
        log.err(msg)
    for commit in all_commits:
      commit, branch = commit
      if not self.svn_mode:
        self.comparator.addRevision(commit['commit'])
      try:
        path = REVISION_DETAIL_TEMPLATE % (self.repo_path, commit['commit'])
        detail = yield self.agent.request('GET', path, retry=5)
        yield self._create_change(detail, branch)
      except Exception:
        msg = ('GitilesPoller: Error while processing revision %s '
               'on branch %s:\n%s' % (
                   commit['commit'], branch, traceback.format_exc()))
        log.err(msg)
    else:
      log.msg('GitilesPoller: No new commits.')

  def describe(self):
    status = self.__class__.__name__
    if not self.master:
      status += ' [STOPPED - check log]'
    return '%s repo_url=%s' % (status, self.repo_url)
