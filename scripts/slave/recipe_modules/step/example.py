# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'step',
]


def GenSteps(api):
  # We are going to have steps with the same name, so fix it automagically.
  api.step.auto_resolve_conflicts = True

  # TODO(martinis) change this
  # The api.step object is directly callable.
  api.step('hello', ['echo', 'Hello World'])
  api.step('hello', ['echo', 'Why hello, there.'])

  # You can also manipulate various aspects of the step, such as env.
  # These are passed straight through to subprocess.Popen.
  # Also, abusing bash -c in this way is a TERRIBLE IDEA DON'T DO IT.
  api.step('goodbye', ['bash', '-c', 'echo Good bye, $friend.'],
           env={'friend': 'Darth Vader'})


def GenTests(api):
  yield api.test('basic')
