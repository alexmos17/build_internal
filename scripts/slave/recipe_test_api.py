# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import collections

from .recipe_util import ModuleInjectionSite, static_call, static_wraps

def combineify(name, dest, a, b):
  """
  Combines dictionary members in two objects into a third one using addition.

  Args:
    name - the name of the member
    dest - the destination object
    a - the first source object
    b - the second source object
  """
  dest_dict = getattr(dest, name)
  dest_dict.update(getattr(a, name))
  for k, v in getattr(b, name).iteritems():
    if k in dest_dict:
      dest_dict[k] += v
    else:
      dest_dict[k] = v


class BaseTestData(object):
  def __init__(self, enabled=True):
    super(BaseTestData, self).__init__()
    self._enabled = enabled

  @property
  def enabled(self):
    return self._enabled


class PlaceholderTestData(BaseTestData):
  def __init__(self, data=None):
    super(PlaceholderTestData, self).__init__()
    self.data = data

  def __repr__(self):
    return "PlaceholderTestData(%r)" % (self.data,)


class StepTestData(BaseTestData):
  """
  Mutable container for per-step test data.

  This data is consumed while running the recipe (during
  annotated_run.run_steps).
  """
  def __init__(self):
    super(StepTestData, self).__init__()
    # { (module, placeholder) -> [data] }
    self.placeholder_data = collections.defaultdict(list)
    self._retcode = None

  def __add__(self, other):
    assert isinstance(other, StepTestData)
    ret = StepTestData()

    combineify('placeholder_data', ret, self, other)

    # pylint: disable=W0212
    ret._retcode = self._retcode
    if other._retcode is not None:
      assert ret._retcode is None
      ret._retcode = other._retcode
    return ret

  def pop_placeholder(self, name_pieces):
    l = self.placeholder_data[name_pieces]
    if l:
      return l.pop(0)
    else:
      return PlaceholderTestData()

  @property
  def retcode(self):  # pylint: disable=E0202
    return self._retcode or 0

  @retcode.setter
  def retcode(self, value):  # pylint: disable=E0202
    self._retcode = value

  def __repr__(self):
    return "StepTestData(%r)" % ({
      'placeholder_data': dict(self.placeholder_data.iteritems()),
      'retcode': self._retcode,
    },)


class ModuleTestData(BaseTestData, dict):
  """
  Mutable container for test data for a specific module.

  This test data is consumed at module load time (i.e. when CreateRecipeApi
  runs).
  """
  def __add__(self, other):
    assert isinstance(other, ModuleTestData)
    ret = ModuleTestData()
    ret.update(self)
    ret.update(other)
    return ret

  def __repr__(self):
    return "ModuleTestData(%r)" % super(ModuleTestData, self).__repr__()


class TestData(BaseTestData):
  def __init__(self, name=None):
    super(TestData, self).__init__()
    self.name = name
    self.properties = {}  # key -> val
    self.mod_data = collections.defaultdict(ModuleTestData)
    self.step_data = collections.defaultdict(StepTestData)

  def __add__(self, other):
    assert isinstance(other, TestData)
    ret = TestData(self.name or other.name)

    ret.properties.update(self.properties)
    ret.properties.update(other.properties)

    combineify('mod_data', ret, self, other)
    combineify('step_data', ret, self, other)

    return ret

  def empty(self):
    return not self.step_data

  def __repr__(self):
    return "TestData(%r)" % ({
      'name': self.name,
      'properties': self.properties,
      'mod_data': dict(self.mod_data.iteritems()),
      'step_data': dict(self.step_data.iteritems()),
    },)


class DisabledTestData(BaseTestData):
  def __init__(self):
    super(DisabledTestData, self).__init__(False)

  def __getattr__(self, name):
    return self

  def pop_placeholder(self, _name_pieces):
    return self


def mod_test_data(func):
  @static_wraps(func)
  def inner(self, *args, **kwargs):
    assert isinstance(self, RecipeTestApi)
    mod_name = self._module.NAME  # pylint: disable=W0212
    ret = TestData(None)
    data = static_call(self, func, *args, **kwargs)
    ret.mod_data[mod_name][inner.__name__] = data
    return ret
  return inner


def placeholder_step_data(func):
  """Decorates RecipeTestApi member functions to allow those functions to
  return just the placeholder data, instead of the normally required
  StepTestData() object.

  The wrapped function may return either:
    * <placeholder data>, <retcode or None>
    * StepTestData containing exactly one PlaceholderTestData and possible a
      retcode. This is useful for returning the result of another method which
      is wrapped with placeholder_step_data.

  In either case, the wrapper function will return a StepTestData object with
  the retcode and placeholder datum inserted with a name of:
    (<Test module name>, <wrapped function name>)

  Say you had a 'foo_module' with the following RecipeTestApi:
    class FooTestApi(RecipeTestApi):
      @placeholder_step_data
      @staticmethod
      def cool_method(data, retcode=None):
        return ("Test data (%s)" % data), retcode

      @placeholder_step_data
      def other_method(self, retcode=None):
        return self.cool_method('hammer time', retcode)

  Code calling cool_method('hello') would get a StepTestData:
    StepTestData(
      placeholder_data = {
        ('foo_module', 'cool_method'): [
          PlaceholderTestData('Test data (hello)')
        ]
      },
      retcode = None
    )

  Code calling other_method(50) would get a StepTestData:
    StepTestData(
      placeholder_data = {
        ('foo_module', 'other_method'): [
          PlaceholderTestData('Test data (hammer time)')
        ]
      },
      retcode = 50
    )
  """
  @static_wraps(func)
  def inner(self, *args, **kwargs):
    assert isinstance(self, RecipeTestApi)
    mod_name = self._module.NAME  # pylint: disable=W0212
    data = static_call(self, func, *args, **kwargs)
    if isinstance(data, StepTestData):
      all_data = [i
                  for l in data.placeholder_data.values()
                  for i in l]
      assert len(all_data) == 1, (
        'placeholder_step_data is only expecting a single placeholder datum. '
        'Got: %r' % data
      )
      placeholder_data, retcode = all_data[0], data.retcode
    else:
      placeholder_data, retcode = data
      placeholder_data = PlaceholderTestData(placeholder_data)

    ret = StepTestData()
    ret.placeholder_data[(mod_name, inner.__name__)].append(placeholder_data)
    ret.retcode = retcode
    return ret
  return inner


class RecipeTestApi(object):
  """Provides testing interface for GenTest method.

  There are two primary components to the test api:
    * Test data creation methods (test and step_data)
    * test_api's from all the modules in DEPS.

  Every test in GenTests(api) takes the form:
    yield <instance of TestData>

  There are 4 basic pieces to TestData:
    name       - The name of the test.
    properties - Simple key-value dictionary which is used as the combined
                 build_properties and factory_properties for this test.
    mod_data   - Module-specific testing data (see the platform module for a
                 good example). This is testing data which is only used once at
                 the start of the execution of the recipe. Modules should
                 provide methods to get their specific test information. See
                 the platform module's test_api for a good example of this.
    step_data  - Step-specific data. There are two major components to this.
        retcode          - The return code of the step
        placeholder_data - A mapping from placeholder name to the a list of
                           PlaceholderTestData objects, one for each instance
                           of that kind of Placeholder in the step.

  TestData objects are concatenatable, so it's convienent to phrase test cases
  as a series of added TestData objects. For example:
    DEPS = ['properties', 'platform', 'json']
    def GenTests(api):
      yield (
        api.test('try_win64') +
        api.properties.tryserver(power_level=9001) +
        api.platform('win', 64) +
        api.step_data(
          'some_step',
          api.json.output("bobface"),
          api.json.output({'key': 'value'})
        )
      )

  This example would run a single test (named 'try_win64') with the standard
  tryserver properties (plus an extra property 'power_level' whose value was
  over 9000).  The test would run as if it were being run on a 64-bit windows
  installation, and the step named 'some_step' would have its first json output
  placeholder be mocked to return '"bobface"', and its second json output
  placeholder be mocked to return '{"key": "value"}'.

  The properties.tryserver() call is documented in the 'properties' module's
  test_api.
  The platform() call is documented in the 'platform' module's test_api.
  The json.output() call is documented in the 'json' module's test_api.
  """
  def __init__(self, module=None, test_data=DisabledTestData()):
    """Note: Injected dependencies are NOT available in __init__()."""
    # If we're the 'root' api, inject directly into 'self'.
    # Otherwise inject into 'self.m'
    self.m = self if module is None else ModuleInjectionSite()
    self._module = module

    assert isinstance(test_data, (ModuleTestData, DisabledTestData))
    self._test_data = test_data

  @staticmethod
  def test(name):
    """Returns a new empty TestData with the name filled in.

    Use in GenTests:
      def GenTests(api):
        yield api.test('basic')
    """
    return TestData(name)

  @staticmethod
  def step_data(name, *data, **kwargs):
    """Returns a new TestData with the mock data filled in for a single step.

    Args:
      name - The name of the step we're providing data for
      data - Zero or more StepTestData objects. These may fill in placeholder
             data for zero or more modules, as well as possibly setting the
             retcode for this step.
      retcode=(int or None) - Override the retcode for this step, even if it
             was set by |data|. This must be set as a keyword arg.

    Use in GenTests:
      def GenTests(api):
        yield (
          api.test('more') +
          api.step_data(
            'init',
            api.json.output({'some': ["cool", "json"]})
          )
        )
    """
    assert all(isinstance(d, StepTestData) for d in data)
    ret = TestData(None)
    if data:
      ret.step_data[name] = reduce(sum, data)
    if 'retcode' in kwargs:
      ret.step_data[name].retcode = kwargs['retcode']
    return ret
