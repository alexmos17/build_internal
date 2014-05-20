# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# Contains the bulk of the WebRTC builder configurations so they can be reused
# from multiple recipes.

RECIPE_CONFIGS = {
  'webrtc': {
    'webrtc_config': 'webrtc',
    'test_suite': 'webrtc',
  },
  'webrtc_baremetal': {
    'webrtc_config': 'webrtc',
    'test_suite': 'webrtc_baremetal',
  },
  'webrtc_clang': {
    'webrtc_config': 'webrtc_clang',
    'test_suite': 'webrtc',
  },
  'webrtc_asan': {
    'webrtc_config': 'webrtc_asan',
    'test_suite': 'webrtc',
  },
  'webrtc_tsan2': {
    'webrtc_config': 'webrtc_tsan2',
    'test_suite': 'webrtc',
  },
  'webrtc_android': {
    'webrtc_config': 'webrtc_android',
  },
  'webrtc_android_clang': {
    'webrtc_config': 'webrtc_android_clang',
  },
  'webrtc_ios': {
    'webrtc_config': 'webrtc_ios',
  },
  'chromium_webrtc': {
    'chromium_config': 'chromium',
    'webrtc_config': 'chromium',
    'gclient_config': 'chromium_webrtc',
    'compile_targets': [
      'chromium_builder_webrtc',
    ],
    'test_suite': 'chromium',
  },
  'chromium_webrtc_tot': {
    'chromium_config': 'chromium',
    'webrtc_config': 'chromium',
    'gclient_config': 'chromium_webrtc_tot',
    'compile_targets': [
      'chromium_builder_webrtc',
    ],
    'test_suite': 'chromium',
  },
  'chromium_webrtc_android': {
    'chromium_config': 'chromium',
    'webrtc_config': 'chromium',
    'gclient_config': 'chromium_webrtc',
    'gclient_apply_config': ['android'],
    'compile_targets': [
      'android_builder_tests',
    ],
    'test_suite': 'chromium',
  },
  'chromium_webrtc_tot_android': {
    'chromium_config': 'chromium',
    'webrtc_config': 'chromium',
    'gclient_config': 'chromium_webrtc_tot',
    'gclient_apply_config': ['android'],
    'compile_targets': [
      'android_builder_tests',
    ],
    'test_suite': 'chromium',
  },
}

BUILDERS = {
  'chromium.webrtc': {
    'builders': {
      'Win Builder': {
        'recipe_config': 'chromium_webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'build_gs_archive': 'win_rel_archive',
        'testing': {
          'platform': 'win',
        },
      },
      'WinXP Tester': {
        'recipe_config': 'chromium_webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'webrtc_config_kwargs': {
          'MEASURE_PERF': True,
        },
        'bot_type': 'tester',
        'build_gs_archive': 'win_rel_archive',
        'disable_runhooks': True,
        'parent_buildername': 'Win Builder',
        'testing': {
          'platform': 'win',
        },
      },
      'Win7 Tester': {
        'recipe_config': 'chromium_webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'webrtc_config_kwargs': {
          'MEASURE_PERF': True,
        },
        'bot_type': 'tester',
        'build_gs_archive': 'win_rel_archive',
        # TODO(kjellander): Disable the hooks on Win7 as soon we've moved away
        # from downloading test resources in that step.
        'disable_runhooks': False,
        'parent_buildername': 'Win Builder',
        'testing': {
          'platform': 'win',
        },
      },
      'Mac Builder': {
        'recipe_config': 'chromium_webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'build_gs_archive': 'mac_rel_archive',
        'testing': {
          'platform': 'mac',
        }
      },
      'Mac Tester': {
        'recipe_config': 'chromium_webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'webrtc_config_kwargs': {
          'MEASURE_PERF': True,
        },
        'bot_type': 'tester',
        'build_gs_archive': 'mac_rel_archive',
        'parent_buildername': 'Mac Builder',
        'testing': {
          'platform': 'mac',
        }
      },
      'Linux Builder': {
        'recipe_config': 'chromium_webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder',
        'build_gs_archive': 'linux_rel_archive',
        'testing': {
          'platform': 'linux',
        },
      },
      'Linux Tester': {
        'recipe_config': 'chromium_webrtc',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'webrtc_config_kwargs': {
          'MEASURE_PERF': True,
        },
        'bot_type': 'tester',
        'build_gs_archive': 'linux_rel_archive',
        'parent_buildername': 'Linux Builder',
        'testing': {
          'platform': 'linux',
        },
      },
      'Android Builder (dbg)': {
        'recipe_config': 'chromium_webrtc_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,

        },
        'bot_type': 'builder',
        'build_gs_archive': 'android_dbg_archive',
        'testing': {
          'platform': 'linux',
        },
      },
      'Android Tests (dbg) (KK Nexus5)': {
        'recipe_config': 'chromium_webrtc_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'webrtc_config_kwargs': {
          'MEASURE_PERF': True,
        },
        'bot_type': 'tester',
        'build_gs_archive': 'android_dbg_archive',
        'parent_buildername': 'Android Builder (dbg)',
        'testing': {
          'platform': 'linux',
        },
      },
      'Android Tests (dbg) (JB Nexus7.2)': {
        'recipe_config': 'chromium_webrtc_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'webrtc_config_kwargs': {
          'MEASURE_PERF': True,
        },
        'bot_type': 'tester',
        'build_gs_archive': 'android_dbg_archive',
        'parent_buildername': 'Android Builder (dbg)',
        'testing': {
          'platform': 'linux',
        },
      },
    },
  },
  'chromium.webrtc.fyi': {
    'builders': {
      'Win Builder': {
        'recipe_config': 'chromium_webrtc_tot',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'build_gs_archive': 'win_rel_archive_fyi',
        'testing': {
          'platform': 'win',
        },
      },
      'WinXP Tester': {
        'recipe_config': 'chromium_webrtc_tot',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'webrtc_config_kwargs': {
          'MEASURE_PERF': True,
        },
        'bot_type': 'tester',
        'build_gs_archive': 'win_rel_archive_fyi',
        'disable_runhooks': True,
        'parent_buildername': 'Win Builder',
        'testing': {
          'platform': 'win',
        },
      },
      'Win7 Tester': {
        'recipe_config': 'chromium_webrtc_tot',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'webrtc_config_kwargs': {
          'MEASURE_PERF': True,
        },
        'bot_type': 'tester',
        'build_gs_archive': 'win_rel_archive_fyi',
        # TODO(kjellander): Disable the hooks on Win7 as soon we've moved away
        # from downloading test resources in that step.
        'disable_runhooks': False,
        'parent_buildername': 'Win Builder',
        'testing': {
          'platform': 'win',
        },
      },
      'Mac': {
        'recipe_config': 'chromium_webrtc_tot',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'webrtc_config_kwargs': {
          'MEASURE_PERF': True,
        },
        'bot_type': 'builder_tester',
        'testing': {
          'platform': 'mac',
        }
      },
      'Linux': {
        'recipe_config': 'chromium_webrtc_tot',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'webrtc_config_kwargs': {
          'MEASURE_PERF': True,
        },
        'bot_type': 'builder_tester',
        'testing': {
          'platform': 'linux',
        },
      },
      'Android Builder (dbg)': {
        'recipe_config': 'chromium_webrtc_tot_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'build_gs_archive': 'android_dbg_archive_fyi',
        'testing': {
          'platform': 'linux',
        },
      },
      'Android Tests (dbg) (KK Nexus5)': {
        'recipe_config': 'chromium_webrtc_tot_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'webrtc_config_kwargs': {
          'MEASURE_PERF': True,
        },
        'bot_type': 'tester',
        'build_gs_archive': 'android_dbg_archive_fyi',
        'parent_buildername': 'Android Builder (dbg)',
        'testing': {
          'platform': 'linux',
        },
      },
      'Android Tests (dbg) (JB Nexus7.2)': {
        'recipe_config': 'chromium_webrtc_tot_android',
        'chromium_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'webrtc_config_kwargs': {
          'MEASURE_PERF': True,
        },
        'bot_type': 'tester',
        'build_gs_archive': 'android_dbg_archive_fyi',
        'parent_buildername': 'Android Builder (dbg)',
        'testing': {
          'platform': 'linux',
        },
      },
    },
  },
  'client.webrtc': {
    'builders': {
      'Win32 Debug': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {
          'platform': 'win',
        },
      },
      'Win32 Release': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {
          'platform': 'win',
        },
      },
      'Win64 Debug': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {
          'platform': 'win',
        },
      },
      'Win64 Release': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {
          'platform': 'win',
        },
      },
      'Win32 Release [large tests]': {
        'recipe_config': 'webrtc_baremetal',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
          'MEASURE_PERF': True,
        },
        'bot_type': 'builder_tester',
        'testing': {
          'platform': 'win',
        },
      },
      'Win Dr Memory Full': {
        'recipe_config': 'webrtc',
        'chromium_apply_config': ['drmemory_full'],
        'gclient_apply_config': ['drmemory'],
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {
          'platform': 'win',
        },
      },
      'Win Dr Memory Light': {
        'recipe_config': 'webrtc',
        'chromium_apply_config': ['drmemory_light'],
        'gclient_apply_config': ['drmemory'],
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {
          'platform': 'win',
        },
      },
      'Mac32 Debug': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {
          'platform': 'mac',
        },
      },
      'Mac32 Release': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {
          'platform': 'mac',
        },
      },
      'Mac64 Debug': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {
          'platform': 'mac',
        },
      },
      'Mac64 Release': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {
          'platform': 'mac',
        },
      },
      'Mac Asan': {
        'recipe_config': 'webrtc_asan',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {
          'platform': 'mac',
        },
      },
      'Mac32 Release [large tests]': {
        'recipe_config': 'webrtc_baremetal',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
          'MEASURE_PERF': True,
        },
        'bot_type': 'builder_tester',
        'testing': {
          'platform': 'mac',
        },
      },
      'iOS Debug': {
        'recipe_config': 'webrtc_ios',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
          'TARGET_ARCH': 'arm',
          'TARGET_PLATFORM': 'ios',
        },
        'bot_type': 'builder',
        'testing': {
          'platform': 'mac',
        },
      },
      'iOS Release': {
        'recipe_config': 'webrtc_ios',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
          'TARGET_ARCH': 'arm',
          'TARGET_PLATFORM': 'ios',
        },
        'bot_type': 'builder',
        'testing': {
          'platform': 'mac',
        },
      },
      'Linux32 Debug': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {
          'platform': 'linux',
        },
      },
      'Linux32 Release': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {
          'platform': 'linux',
        },
      },
      'Linux64 Debug': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {
          'platform': 'linux',
        },
      },
      'Linux64 Release': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {
          'platform': 'linux',
        },
      },
      'Linux Asan': {
        'recipe_config': 'webrtc_asan',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {
          'platform': 'linux',
        },
      },
      'Linux Memcheck': {
        'recipe_config': 'webrtc',
        'chromium_apply_config': ['memcheck'],
        'gclient_apply_config': ['valgrind'],
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {
          'platform': 'linux',
        },
      },
      'Linux TSan': {
        'recipe_config': 'webrtc',
        'chromium_apply_config': ['tsan'],
        'gclient_apply_config': ['valgrind'],
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {
          'platform': 'linux',
        },
      },
      'Linux TSan v2': {
        'recipe_config': 'webrtc_tsan2',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {
          'platform': 'linux',
        },
      },
      'Linux64 Release [large tests]': {
        'recipe_config': 'webrtc_baremetal',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
          'MEASURE_PERF': True,
        },
        'bot_type': 'builder_tester',
        'testing': {
          'platform': 'linux',
        },
      },
      'Chrome OS': {
        'recipe_config': 'webrtc',
        'chromium_apply_config': ['chromeos'],
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {
          'platform': 'linux',
        },
      },
      'Android': {
        'recipe_config': 'webrtc_android',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {
          'platform': 'linux',
        },
      },
      'Android (dbg)': {
        'recipe_config': 'webrtc_android',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {
          'platform': 'linux',
        },
      },
      'Android Clang (dbg)': {
        'recipe_config': 'webrtc_android_clang',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {
          'platform': 'linux',
        },
      },
    },
  },
  'client.webrtc.fyi': {
    'builders':  {
      'Linux TsanRV': {
        'recipe_config': 'webrtc',
        'chromium_apply_config': ['tsan_race_verifier'],
        'gclient_apply_config': ['valgrind'],
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {
          'platform': 'linux',
        },
      },
    },
  },
  'tryserver.webrtc': {
    'builders': {
      'win': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {
          'platform': 'win',
        },
      },
      'win_rel': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {
          'platform': 'win',
        },
      },
      'win_x64_rel': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {
          'platform': 'win',
        },
      },
      'win_baremetal': {
        'recipe_config': 'webrtc_baremetal',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {
          'platform': 'win',
        },
      },
      'win_drmemory_light': {
        'recipe_config': 'webrtc',
        'chromium_apply_config': ['drmemory_light'],
        'gclient_apply_config': ['drmemory'],
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {
          'platform': 'win',
        },
      },
      'mac': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {
          'platform': 'mac',
        },
      },
      'mac_rel': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {
          'platform': 'mac',
        },
      },
      'mac_x64_rel': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {
          'platform': 'mac',
        },
      },
      'mac_asan': {
        'recipe_config': 'webrtc_asan',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {
          'platform': 'mac',
        },
      },
      'mac_baremetal': {
        'recipe_config': 'webrtc_baremetal',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder_tester',
        'testing': {
          'platform': 'mac',
        },
      },
      'ios': {
        'recipe_config': 'webrtc_ios',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 32,
          'TARGET_ARCH': 'arm',
          'TARGET_PLATFORM': 'ios',
        },
        'bot_type': 'builder',
        'testing': {
          'platform': 'mac',
        },
      },
      'ios_rel': {
        'recipe_config': 'webrtc_ios',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 32,
          'TARGET_ARCH': 'arm',
          'TARGET_PLATFORM': 'ios',
        },
        'bot_type': 'builder',
        'testing': {
          'platform': 'mac',
        },
      },
      'linux': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_rel': {
        'recipe_config': 'webrtc',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_asan': {
        'recipe_config': 'webrtc_asan',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_memcheck': {
        'recipe_config': 'webrtc',
        'chromium_apply_config': ['memcheck'],
        'gclient_apply_config': ['valgrind'],
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_tsan': {
        'recipe_config': 'webrtc',
        'chromium_apply_config': ['tsan'],
        'gclient_apply_config': ['valgrind'],
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_tsan2': {
        'recipe_config': 'webrtc_tsan2',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {
          'platform': 'linux',
        },
      },
      'linux_baremetal': {
        'recipe_config': 'webrtc_baremetal',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_BITS': 64,
        },
        'bot_type': 'builder_tester',
        'testing': {
          'platform': 'linux',
        },
      },
      'android': {
        'recipe_config': 'webrtc_android',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {
          'platform': 'linux',
        },
      },
      'android_rel': {
        'recipe_config': 'webrtc_android',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Release',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {
          'platform': 'linux',
        },
      },
      'android_clang': {
        'recipe_config': 'webrtc_android_clang',
        'webrtc_config_kwargs': {
          'BUILD_CONFIG': 'Debug',
          'TARGET_PLATFORM': 'android',
          'TARGET_ARCH': 'arm',
          'TARGET_BITS': 32,
        },
        'bot_type': 'builder',
        'testing': {
          'platform': 'linux',
        },
      },
    },
  },
}

