# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import functools
import contextlib
import json

from cStringIO import StringIO

from slave import recipe_api
from slave import recipe_util

from .util import TestResults

class StringListIO(object):
  def __init__(self):
    self.lines = [StringIO()]

  def write(self, s):
    while s:
      i = s.find('\n')
      if i == -1:
        self.lines[-1].write(s)
        break
      self.lines[-1].write(s[:i])
      self.lines[-1] = self.lines[-1].getvalue()
      self.lines.append(StringIO())
      s = s[i+1:]

  def close(self):
    if not isinstance(self.lines[-1], basestring):
      self.lines[-1] = self.lines[-1].getvalue()


class JsonOutputPlaceholder(recipe_util.Placeholder):
  """JsonOutputPlaceholder is meant to be a placeholder object which, when added
  to a step's cmd list, will be replaced by annotated_run with the command
  parameters --output-json /path/to/file during the evaluation of your recipe
  generator.

  This placeholder can be optionally added when you use the Steps.step()
  method in this module.

  After the termination of the step, this file is expected to contain a valid
  JSON document, which will be set as the json_output for that step in the
  step_history OrderedDict passed to your recipe generator.
  """
  def __init__(self, api):
    self.raw = api.m.raw_io.output('.json')
    super(JsonOutputPlaceholder, self).__init__()

  def render(self, test):
    return self.raw.render(test)

  def result(self, presentation, test):
    raw_data = self.raw.result(presentation, test)

    valid = False
    ret = None
    try:
      ret = json.loads(raw_data)
      valid = True
    except ValueError:  # pragma: no cover
      pass

    key = self.name + ('' if valid else ' (invalid)')
    with contextlib.closing(StringListIO()) as listio:
      json.dump(ret, listio, indent=2, sort_keys=True)
    presentation.logs[key] = listio.lines

    return ret


class TestResultsOutputPlaceholder(JsonOutputPlaceholder):
  def result(self, presentation, test):
    ret = super(TestResultsOutputPlaceholder, self).result(presentation, test)
    return TestResults(ret)


class JsonApi(recipe_api.RecipeApi):
  def __init__(self, **kwargs):
    super(JsonApi, self).__init__(**kwargs)
    self.loads = json.loads
    @functools.wraps(json.dumps)
    def dumps(*args, **kwargs):
      kwargs['sort_keys'] = True
      return json.dumps(*args, **kwargs)
    self.dumps = dumps

  @recipe_util.returns_placeholder
  def input(self, data):
    """A placeholder which will expand to a file path containing <data>."""
    return self.m.raw_io.input(self.dumps(data), '.json')

  @recipe_util.returns_placeholder
  def output(self):
    """A placeholder which will expand to '--output-json /tmp/file'."""
    return JsonOutputPlaceholder(self)

  @recipe_util.returns_placeholder
  def test_results(self):
    """A placeholder which will expand to '--json-test-results /tmp/file'.

    The test_results will be an instance of the TestResults class.
    """
    return TestResultsOutputPlaceholder(self)

  def property_args(self):
    """Return --build-properties and --factory-properties arguments. LEGACY!

    Since properties is the merge of build_properties and factory_properties,
    pass the merged dict as both arguments.

    It's vastly preferable to have your recipe only pass the bare minimum
    of arguments to steps. Passing property objects obscures the data that
    the script actually consumes from the property object.
    """
    prop_str = self.dumps(dict(self.m.properties))
    return [
      '--factory-properties', prop_str,
      '--build-properties', prop_str
    ]
