# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.schedulers.basic import SingleBranchScheduler

from main.factory import annotator_factory

m_annotator = annotator_factory.AnnotatorFactory()

def Update(c):
  c['schedulers'].extend([
      SingleBranchScheduler(name='webrtc_mac_scheduler',
                            branch='trunk',
                            treeStableTimer=30,
                            builderNames=[
          'Mac32 Debug',
          'Mac32 Release',
          'Mac64 Debug',
          'Mac64 Release',
          'Mac32 Release [large tests]',
          'Mac Asan',
          'iOS Debug',
          'iOS Release',
      ]),
  ])

  # 'subordinatebuilddir' below is used to reduce the number of checkouts since some
  # of the builders are pooled over multiple subordinate machines.
  specs = [
    {'name': 'Mac32 Debug', 'subordinatebuilddir': 'mac32'},
    {'name': 'Mac32 Release', 'subordinatebuilddir': 'mac32'},
    {'name': 'Mac64 Debug', 'subordinatebuilddir': 'mac64'},
    {'name': 'Mac64 Release', 'subordinatebuilddir': 'mac64'},
    {
      'name': 'Mac32 Release [large tests]',
      'category': 'compile|baremetal',
      'subordinatebuilddir': 'mac_baremetal',
    },
    {'name': 'Mac Asan', 'subordinatebuilddir': 'mac_asan'},
    {'name': 'iOS Debug', 'subordinatebuilddir': 'ios'},
    {'name': 'iOS Release', 'subordinatebuilddir': 'ios'},
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_annotator.BaseFactory('webrtc/standalone'),
        'notify_on_missing': True,
        'category': spec.get('category', 'compile|testers'),
        'subordinatebuilddir': spec['subordinatebuilddir'],
      } for spec in specs
  ])
