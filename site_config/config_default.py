# Copyright 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Seeds a number of variables defined in chromium_config.py.

The recommended way is to fork this file and use a custom DEPS forked from
config/XXX/DEPS with the right configuration data."""

import socket


class classproperty(object):
  """A decorator that allows is_production_host to only to be defined once."""
  def __init__(self, getter):
    self.getter = getter
  def __get__(self, instance, owner):
    return self.getter(owner)


class Main(object):
  # Repository URLs used by the SVNPoller and 'gclient config'.
  server_url = 'http://src.chromium.org'
  repo_root = '/svn'
  git_server_url = 'https://chromium.googlesource.com'

  # External repos.
  googlecode_url = 'http://%s.googlecode.com/svn'
  sourceforge_url = 'https://svn.code.sf.net/p/%(repo)s/code'
  googlecode_revlinktmpl = 'https://code.google.com/p/%s/source/browse?r=%s'

  # Directly fetches from anonymous Blink svn server.
  webkit_root_url = 'http://src.chromium.org/blink'
  nacl_trunk_url = 'http://src.chromium.org/native_client/trunk'

  llvm_url = 'http://llvm.org/svn/llvm-project'

  # Perf Dashboard upload URL.
  dashboard_upload_url = 'https://chromeperf.appspot.com'

  # Actually for Chromium OS subordinates.
  chromeos_url = git_server_url + '/chromiumos.git'

  # Default domain for emails to come from and
  # domains to which emails can be sent.
  main_domain = 'example.com'
  permitted_domains = ('example.com',)

  # Your smtp server to enable mail notifications.
  smtp = 'smtp'

  # By default, bot_password will be filled in by config.GetBotPassword().
  bot_password = None

  # Fake urls to make various factories happy.
  swarm_server_internal_url = 'http://fake.swarm.url.server.com'
  swarm_server_dev_internal_url = 'http://fake.swarm.dev.url.server.com'
  swarm_hashtable_server_internal = 'http://fake.swarm.hashtable.server.com'
  swarm_hashtable_server_dev_internal = 'http://fake.swarm.hashtable.server.com'
  trunk_internal_url = None
  trunk_internal_url_src = None
  subordinate_internal_url = None
  git_internal_server_url = None
  syzygy_internal_url = None
  v8_internal_url = None


  class Base(object):
    """Main base template.
    Contains stubs for variables that all mains must define."""
    # Main address. You should probably copy this file in another svn repo
    # so you can override this value on both the subordinates and the main.
    main_host = 'localhost'
    # Only report that we are running on a main if the main_host (even when
    # main_host is overridden by a subclass) is the same as the current host.
    @classproperty
    def is_production_host(cls):
      return socket.getfqdn() == cls.main_host
    # 'from:' field for emails sent from the server.
    from_address = 'nobody@example.com'
    # Additional email addresses to send gatekeeper (automatic tree closage)
    # notifications. Unnecessary for experimental mains and try servers.
    tree_closing_notification_recipients = []
    # For the following values, they are used only if non-0. Do not set them
    # here, set them in the actual main configuration class:
    # Used for the waterfall URL and the waterfall's WebStatus object.
    main_port = 0
    # Which port subordinates use to connect to the main.
    subordinate_port = 0
    # The alternate read-only page. Optional.
    main_port_alt = 0

  ## Per-main configs.

  class Main1(Base):
    """Chromium main."""
    main_host = 'main1.golo.chromium.org'
    from_address = 'buildbot@chromium.org'
    tree_closing_notification_recipients = [
        'chromium-build-failure@chromium-gatekeeper-sentry.appspotmail.com']
    base_app_url = 'https://chromium-status.appspot.com'
    tree_status_url = base_app_url + '/status'
    store_revisions_url = base_app_url + '/revisions'
    last_good_url = base_app_url + '/lkgr'
    last_good_blink_url = 'http://blink-status.appspot.com/lkgr'

  class Main2(Base):
    """Chromeos main."""
    main_host = 'main2.golo.chromium.org'
    tree_closing_notification_recipients = [
        'chromeos-build-failures@google.com']
    from_address = 'buildbot@chromium.org'

  class Main3(Base):
    """Client main."""
    main_host = 'main3.golo.chromium.org'
    tree_closing_notification_recipients = []
    from_address = 'buildbot@chromium.org'

  class Main4(Base):
    """Try server main."""
    main_host = 'main4.golo.chromium.org'
    tree_closing_notification_recipients = []
    from_address = 'tryserver@chromium.org'
    code_review_site = 'https://codereview.chromium.org'

  class Main4a(Base):
    """Try server main."""
    main_host = 'main4a.golo.chromium.org'
    tree_closing_notification_recipients = []
    from_address = 'tryserver@chromium.org'
    code_review_site = 'https://codereview.chromium.org'

  ## Native Client related

  class NaClBase(Main3):
    """Base class for Native Client mains."""
    tree_closing_notification_recipients = ['bradnelson@chromium.org']
    base_app_url = 'https://nativeclient-status.appspot.com'
    tree_status_url = base_app_url + '/status'
    store_revisions_url = base_app_url + '/revisions'
    last_good_url = base_app_url + '/lkgr'
    perf_base_url = 'http://build.chromium.org/f/client/perf'

  ## ChromiumOS related

  class ChromiumOSBase(Main2):
    """Base class for ChromiumOS mains"""
    base_app_url = 'https://chromiumos-status.appspot.com'
    tree_status_url = base_app_url + '/status'
    store_revisions_url = base_app_url + '/revisions'
    last_good_url = base_app_url + '/lkgr'
