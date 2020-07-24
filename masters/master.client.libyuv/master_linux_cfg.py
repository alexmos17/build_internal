# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.schedulers.basic import SingleBranchScheduler

from main.factory import annotator_factory

m_annotator = annotator_factory.AnnotatorFactory()

def Update(c):
  c['schedulers'].extend([
      SingleBranchScheduler(name='libyuv_linux_scheduler',
                            branch='trunk',
                            treeStableTimer=0,
                            builderNames=[
          'Linux32 Debug',
          'Linux32 Release',
          'Linux64 Debug',
          'Linux64 Release',
          'Linux Asan',
          'Linux Memcheck',
          'Linux Tsan v2',
      ]),
  ])

  specs = [
    {'name': 'Linux32 Debug', 'subordinatebuilddir': 'linux32'},
    {'name': 'Linux32 Release', 'subordinatebuilddir': 'linux32'},
    {'name': 'Linux64 Debug', 'subordinatebuilddir': 'linux64'},
    {'name': 'Linux64 Release', 'subordinatebuilddir': 'linux64'},
    {'name': 'Linux Asan', 'subordinatebuilddir': 'linux_asan'},
    {'name': 'Linux Memcheck', 'subordinatebuilddir': 'linux_memcheck_tsan'},
    {'name': 'Linux Tsan v2', 'subordinatebuilddir': 'linux_tsan2'},
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        'factory': m_annotator.BaseFactory('libyuv/libyuv'),
        'notify_on_missing': True,
        'category': 'linux',
        'subordinatebuilddir': spec['subordinatebuilddir'],
      } for spec in specs
  ])
