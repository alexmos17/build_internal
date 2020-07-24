# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from main import gatekeeper
from main import main_utils

# This is the list of the builder categories and the corresponding critical
# steps. If one critical step fails, gatekeeper will close the tree
# automatically.
# Note: don't include 'update scripts' since we can't do much about it when
# it's failing and the tree is still technically fine.
categories_steps = {
  '': ['update', 'runhooks', 'compile'],
  'testers': [
    'audio_decoder_unittests',
    'common_audio_unittests',
    'common_video_unittests',
    'libjingle_media_unittest',
    'libjingle_p2p_unittest',
    'libjingle_peerconnection_unittest',
    'libjingle_unittest',
    'modules_tests',
    'modules_unittests',
    'system_wrappers_unittests',
    'test_support_unittests',
    'tools_unittests',
    'video_engine_core_unittests',
    'video_engine_tests',
    'voice_engine_unittests',
  ],
  'baremetal': [
    'webrtc_perf_tests',
  ],
  'windows': ['svnkill', 'taskkill'],
  'compile': ['compile', 'archive_build'],
  # Annotator scripts are triggered as a 'subordinate_steps' step.
  # The gatekeeper currently does not recognize failure in a
  # @@@BUILD_STEP@@@, so we must match on the buildbot-defined step.
  'android': ['subordinate_steps'],
}

exclusions = {
}

forgiving_steps = ['update_scripts', 'update', 'svnkill', 'taskkill',
                   'archive_build', 'start_crash_handler', 'gclient_revert']

def Update(config, active_main, c):
  lookup = main_utils.FilterDomain(
      domain=active_main.main_domain,
      permitted_domains=active_main.permitted_domains)

  c['status'].append(gatekeeper.GateKeeper(
      fromaddr=active_main.from_address,
      categories_steps=categories_steps,
      exclusions=exclusions,
      relayhost=config.Main.smtp,
      subject='buildbot %(result)s in %(projectName)s on %(builder)s, '
              'revision %(revision)s',
      extraRecipients=active_main.tree_closing_notification_recipients,
      lookup=lookup,
      forgiving_steps=forgiving_steps,
      tree_status_url=active_main.tree_status_url))
