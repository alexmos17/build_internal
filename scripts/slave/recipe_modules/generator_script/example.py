# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'generator_script',
  'json',
  'path',
  'step',
]


def GenSteps(api):
  api.path['checkout'] = api.path['subordinate_build']
  api.generator_script('bogus')
  api.generator_script('bogus.py', env={'FOO': 'bar'})
  api.generator_script('presentation.py')

def GenTests(api):
  mock_json = {
    'mock': 'data',
  }
  yield (
    api.test('basic') +
    api.generator_script(
      'bogus',
      {'name': 'mock.step.binary', 'cmd': ['echo', 'mock step binary']}
    ) +
    api.generator_script(
      'bogus.py',
      {'name': 'mock.step.python', 'cmd': ['echo', 'mock step python']}
    ) +
    api.generator_script(
      'presentation.py', {
        'name': 'mock.step.presentation',
        'cmd': ['echo', 'mock step presentation'],
        'outputs_presentation_json': True
      }
    ) +
    api.step_data(
      'mock.step.presentation',
      api.json.output({'step_text': 'mock step text'})
    )
  )
