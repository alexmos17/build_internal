#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import os
import unittest

import test_env  # pylint: disable=W0403,W0611

from slave import extract_build
from slave import slave_utils

# build/scripts/slave/unittests
_SCRIPT_DIR = os.path.dirname(__file__)
_BUILD_DIR = os.path.abspath(os.path.join(
    _SCRIPT_DIR, os.pardir, os.pardir))


class MockOptions(object):
  webkit_dir = None
  build_properties = {}
  factory_properties = {}


class ExtractBuildTest(unittest.TestCase):
  def testGetBuildUrl(self):
    options = MockOptions()

    # version_suffix is not tested, since it would just be copying of
    # implementation details from extract_build.py into this test.
    src_dir = os.path.dirname(_BUILD_DIR)
    base_filename, _version_suffix = slave_utils.GetZipFileNames(
        options.build_properties, src_dir, None, extract=True)

    gs_url_without_slash = 'gs://foo/Win'
    gs_url_with_slash = 'gs://foo/Win/'
    gs_url_with_filename = 'gs://foo/Win/%s.zip' % base_filename
    http_url_without_slash = 'http://foo/Win'
    http_url_with_slash = 'http://foo/Win/'
    http_url_with_filename = 'http://foo/Win/%s.zip' % base_filename
    expected_gs_url = gs_url_with_slash + base_filename + '.zip'
    expected_http_url = http_url_with_slash + base_filename + '.zip'

    # Verify that only one slash is added: URL without ending slash.
    self._VerifyBuildUrl(options, gs_url_without_slash, expected_gs_url)
    self._VerifyBuildUrl(options, http_url_without_slash, expected_http_url)

    # URL with ending slash.
    self._VerifyBuildUrl(options, gs_url_with_slash, expected_gs_url)
    self._VerifyBuildUrl(options, http_url_with_slash, expected_http_url)

    # URL with filename.
    self._VerifyBuildUrl(options, gs_url_with_filename, expected_gs_url)
    self._VerifyBuildUrl(options, http_url_with_filename, expected_http_url)

  def _VerifyBuildUrl(self, options, url_template, expected_url):
    options.build_url = url_template
    url, _versioned_url = extract_build.GetBuildUrl(_BUILD_DIR, options)
    self.assertEquals(url, expected_url)

if __name__ == '__main__':
  unittest.main()
