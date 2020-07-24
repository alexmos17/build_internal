# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


from main import main_config
from main.factory import annotator_factory

import collections

defaults = {}

helper = main_config.Helper(defaults)
B = helper.Builder
F = helper.Factory
T = helper.Triggerable

# TODO(kbr): it would be better if this waterfall were refactored so
# that we could access the subordinates_list here.
gpu_subordinate_info = [
  {
    'builder': 'GPU Win Builder',
    'factory_id': 'f_gpu_win_builder_rel',
    'recipe': 'gpu/build_and_upload',
    'build_config': 'Release',
  },
  {
    'builder': 'GPU Win Builder (dbg)',
    'factory_id': 'f_gpu_win_builder_dbg',
    'recipe': 'gpu/build_and_upload',
    'build_config': 'Debug',
  },
  {
    'builder': 'GPU Win7 (NVIDIA)',
    'factory_id': 'f_gpu_win_rel',
    'recipe': 'gpu/download_and_test',
    'build_config': 'Release',
    'perf_id': 'gpu-webkit-win7-nvidia',
    'triggered_by': 'GPU Win Builder',
    'auto_reboot': False,
  },
  {
    'builder': 'GPU Win7 (dbg) (NVIDIA)',
    'factory_id': 'f_gpu_win_dbg',
    'recipe': 'gpu/download_and_test',
    'build_config': 'Debug',
    'triggered_by': 'GPU Win Builder (dbg)',
    'auto_reboot': False,
  },
  {
    'builder': 'GPU Mac Builder',
    'factory_id': 'f_gpu_mac_builder_rel',
    'recipe': 'gpu/build_and_upload',
    'build_config': 'Release',
  },
  {
    'builder': 'GPU Mac Builder (dbg)',
    'factory_id': 'f_gpu_mac_builder_dbg',
    'recipe': 'gpu/build_and_upload',
    'build_config': 'Debug',
  },
  {
    'builder': 'GPU Mac10.7',
    'factory_id': 'f_gpu_mac_rel',
    'recipe': 'gpu/download_and_test',
    'build_config': 'Release',
    'perf_id': 'gpu-webkit-mac',
    'triggered_by': 'GPU Mac Builder',
  },
  {
    'builder': 'GPU Mac10.7 (dbg)',
    'factory_id': 'f_gpu_mac_dbg',
    'recipe': 'gpu/download_and_test',
    'build_config': 'Debug',
    'triggered_by': 'GPU Mac Builder (dbg)',
  },
  {
    'builder': 'GPU Mac 10.9 (Intel)',
    'factory_id': 'f_gpu_mac_10_9_rel',
    'recipe': 'gpu/download_and_test',
    'build_config': 'Release',
    'perf_id': 'gpu-webkit-mac',
    'triggered_by': 'GPU Mac Builder',
  },
  {
    'builder': 'GPU Mac 10.9 (Intel) (dbg)',
    'factory_id': 'f_gpu_mac_10_9_dbg',
    'recipe': 'gpu/download_and_test',
    'build_config': 'Debug',
    'triggered_by': 'GPU Mac Builder (dbg)',
  },
  {
    'builder': 'GPU Linux Builder',
    'factory_id': 'f_gpu_linux_builder_rel',
    'recipe': 'gpu/build_and_upload',
    'build_config': 'Release',
  },
  {
    'builder': 'GPU Linux Builder (dbg)',
    'factory_id': 'f_gpu_linux_builder_dbg',
    'recipe': 'gpu/build_and_upload',
    'build_config': 'Debug',
  },
  {
    'builder': 'GPU Linux (NVIDIA)',
    'factory_id': 'f_gpu_linux_rel',
    'recipe': 'gpu/download_and_test',
    'build_config': 'Release',
    'perf_id': 'gpu-webkit-linux-nvidia',
    'triggered_by': 'GPU Linux Builder',
    'auto_reboot': False,
  },
  {
    'builder': 'GPU Linux (dbg) (NVIDIA)',
    'factory_id': 'f_gpu_linux_dbg',
    'recipe': 'gpu/download_and_test',
    'build_config': 'Debug',
    'triggered_by': 'GPU Linux Builder (dbg)',
    'auto_reboot': False,
  },
]

m_annotator = annotator_factory.AnnotatorFactory()

defaults['category'] = 'gpu'

# Maps the parent builder to a set of the names of the builders it triggers.
trigger_map = collections.defaultdict(list)
# Maps the name of the parent builder to the (synthesized) name of its
# trigger, wrapped in a list.
trigger_name_map = {}
next_group_id = 0
# Note this code is very similar to that in recipe_main_helper.py.
# Unfortunately due to the different structure of this waterfall it's
# impossible to share the code.
def BuilderExists(builder_name):
  for s in gpu_subordinate_info:
    if s['builder'] == builder_name:
      return True
  return False

for subordinate in gpu_subordinate_info:
  builder = subordinate['builder']
  parent_builder = subordinate.get('triggered_by')
  if parent_builder is not None:
    if not BuilderExists(parent_builder):
      raise Exception('Could not find parent builder %s for builder %s' %
                      (parent_builder, builder))
    trigger_map[parent_builder].append(builder)
    if parent_builder not in trigger_name_map:
      trigger_name_map[parent_builder] = 'trigger_group_%d' % next_group_id
      next_group_id += 1

# Create triggers
for trigger_name in trigger_name_map.values():
  T(trigger_name)

# Set up bots
for subordinate in gpu_subordinate_info:
  factory_properties = {
    'test_results_server': 'test-results.appspot.com',
    'generate_gtest_json': True,
    'build_config': subordinate['build_config'],
    'top_of_tree_blink': True
  }
  if 'perf_id' in subordinate:
    factory_properties['show_perf_results'] = True
    factory_properties['perf_id'] = subordinate['perf_id']
  name = subordinate['builder']
  scheduler = 'global_scheduler'
  if 'triggered_by' in subordinate:
    scheduler = trigger_name_map[subordinate['triggered_by']]
  # The default for auto_reboot should match the setting in
  # main_config.py.
  auto_reboot = subordinate.get('auto_reboot', True)
  B(name, subordinate['factory_id'], scheduler=scheduler, auto_reboot=auto_reboot)
  F(subordinate['factory_id'], m_annotator.BaseFactory(
    subordinate['recipe'],
    factory_properties,
    [trigger_name_map[name]] if name in trigger_name_map else None))


def Update(_config, _active_main, c):
  return helper.Update(c)
