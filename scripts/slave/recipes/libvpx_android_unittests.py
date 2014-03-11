# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'git',
    'path',
    'platform',
    'properties',
    'python',
    'step',
]

# Constants
ANDROID_TOOLS_GIT = 'https://chromium.googlesource.com/android_tools'
TEST_FILES_URL = 'http://downloads.webmproject.org/test_data/libvpx'

# Device root is a special folder on the device which we have permissions to
# read / write
DEVICE_ROOT = "/data/local/tmp"

# TODO (joshualitt) the configure script is messed up so we need a relative
# path.  Essentially, it must be using argv[0] when invoking some of the
# scripts in the libvpx directory
CONFIGURE_PATH_REL = './libvpx/configure'

def GenSteps(api):
  api.step.auto_resolve_conflicts = True

  # Paths and other constants
  build_root = api.path['slave_build']

  # Android tools DEPS
  android_tools_root = build_root('android_tools')
  adb = android_tools_root('sdk', 'platform-tools', 'adb')
  ndk_root = android_tools_root('ndk')

  # libvpx paths
  libvpx_git_url = api.properties['libvpx_git_url']
  libvpx_root = build_root('libvpx')
  test_data = build_root('test_data')

  yield api.python.inline(
      'clean_build', r"""
          import os, sys, shutil
          root = sys.argv[1]
          nuke_dirs = sys.argv[2:]
          for fname in os.listdir(root):
            path = os.path.join(root, fname)
            if os.path.isfile(path):
              os.unlink(path)
            elif fname in nuke_dirs:
              shutil.rmtree(path)
      """, args=[build_root, 'libs', 'obj', 'armeabi-v7a'])

  # Checkout android_tools and libvpx.  NDK and SDK are required to build
  # libvpx for android
  yield api.git.checkout(
      ANDROID_TOOLS_GIT, dir_path=android_tools_root, recursive=True)
  yield api.git.checkout(
      libvpx_git_url, dir_path=libvpx_root, recursive=True)

  yield api.step(
      'configure', [
          CONFIGURE_PATH_REL, '--disable-examples', '--disable-install-docs',
          '--disable-install-srcs', '--disable-unit-tests',
          '--disable-vp8-encoder', '--disable-vp9-encoder',
          '--enable-decode-perf-tests', '--enable-external-build',
          '--enable-vp8-decoder', '--enable-vp9-decoder',
          '--sdk-path=%s' % ndk_root, '--target=armv7-android-gcc'])

  # NDK requires NDK_PROJECT_PATH environment variable to be defined
  yield api.step(
      'ndk-build', [
          ndk_root('ndk-build'),
          'APP_BUILD_SCRIPT=%s'
              % libvpx_root('test', 'android', 'Android.mk'),
          'APP_ABI=armeabi-v7a', 'APP_PLATFORM=android-14',
          'APP_OPTIM=release', 'APP_STL=gnustl_static'],
      env={'NDK_PROJECT_PATH' : build_root})

  test_root = libvpx_root('test')
  yield api.python(
      'get_files', test_root('android', 'get_files.py'),
      args=[
          '-i', test_root('test-data.sha1'),
          '-o', test_data, '-u', TEST_FILES_URL])

  yield api.python(
      'transfer_files',
      api.path['build'].join('scripts', 'slave', 'android',
                             'transfer_files.py'),
      args=[adb, DEVICE_ROOT, test_data])

  lib_root = build_root('libs', 'armeabi-v7a')
  yield api.step('push_so', [ adb, 'push', lib_root, DEVICE_ROOT])

  yield api.step(
      'shell', [
          adb, 'shell', 'LD_LIBRARY_PATH=' + DEVICE_ROOT,
          'LIBVPX_TEST_DATA_PATH=' + DEVICE_ROOT, DEVICE_ROOT + '/vpx_test'])

def GenTests(api):
  # Right now we just support linux, but one day we will have mac and windows
  # as well
  yield (
    api.test('basic_linux_64') +
    api.properties(
        libvpx_git_url='https://chromium.googlesource.com/webm/libvpx'))
