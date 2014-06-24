# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'git',
  'path',
  'platform',
  'properties',
]


def GenSteps(api):
  url = 'https://chromium.googlesource.com/chromium/src.git'

  # git.checkout can optionally dump GIT_CURL_VERBOSE traces to a log file,
  # useful for debugging git access issues that are reproducible only on bots.
  curl_trace_file = None
  if api.properties.get('use_curl_trace'):
    curl_trace_file = api.path['slave_build'].join('curl_trace.log')

  # You can use api.git.checkout to perform all the steps of a safe checkout.
  yield api.git.checkout(
      url,
      ref=api.properties.get('revision'),
      recursive=True,
      curl_trace_file=curl_trace_file)

  # You can use api.git.fetch_tags to fetch all tags from the origin
  yield api.git.fetch_tags()

  # If you need to run more arbitrary git commands, you can use api.git itself,
  # which behaves like api.step(), but automatically sets the name of the step.
  yield api.git('status', cwd=api.path['checkout'])


def GenTests(api):
  yield api.test('basic')
  yield api.test('basic_ref') + api.properties(revision='refs/foo/bar')
  yield api.test('basic_branch') + api.properties(revision='refs/heads/testing')
  yield api.test('basic_hash') + api.properties(
      revision='abcdef0123456789abcdef0123456789abcdef01')

  yield api.test('platform_win') + api.platform.name('win')

  yield api.test('curl_trace_file') + api.properties(
      revision='refs/foo/bar', use_curl_trace=True)
