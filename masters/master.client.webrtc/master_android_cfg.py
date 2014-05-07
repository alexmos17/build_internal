# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.scheduler import Triggerable
from buildbot.schedulers.basic import SingleBranchScheduler

from master.factory import annotator_factory

m_annotator = annotator_factory.AnnotatorFactory()

def Update(c):
  c['schedulers'].extend([
      SingleBranchScheduler(name='webrtc_android_scheduler',
                            branch='trunk',
                            treeStableTimer=0,
                            builderNames=[
          'Android',
          'Android (dbg)',
          'Android Clang (dbg)',
          'Android Chromium-APK Builder',
          'Android Chromium-APK Builder (dbg)',
      ]),
      Triggerable(name='android_trigger_dbg', builderNames=[
          'Android Chromium-APK Tests (KK Nexus5)(dbg)',
          'Android Chromium-APK Tests (JB Nexus7.2)(dbg)',
      ]),
      Triggerable(name='android_trigger_rel', builderNames=[
          'Android Chromium-APK Tests (KK Nexus5)',
          'Android Chromium-APK Tests (JB Nexus7.2)',
      ]),
  ])
  specs = [
    {'name': 'Android', 'recipe': 'webrtc/standalone'},
    {'name': 'Android (dbg)', 'recipe': 'webrtc/standalone'},
    {'name': 'Android Clang (dbg)', 'recipe': 'webrtc/standalone'},
    {
      'name': 'Android Chromium-APK Builder',
      'triggers': ['android_trigger_rel'],
    },
    {
      'name': 'Android Chromium-APK Builder (dbg)',
      'triggers': ['android_trigger_dbg'],
    },
    {'name': 'Android Chromium-APK Tests (KK Nexus5)(dbg)'},
    {'name': 'Android Chromium-APK Tests (JB Nexus7.2)(dbg)'},
    {'name': 'Android Chromium-APK Tests (KK Nexus5)'},
    {'name': 'Android Chromium-APK Tests (JB Nexus7.2)'},
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_annotator.BaseFactory(
            spec.get('recipe', 'webrtc/android_apk'),
            triggers=spec.get('triggers')),
        'notify_on_missing': True,
        'category': 'android',
      } for spec in specs
  ])
