# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import difflib
import json
import os
import pprint

try:
  import yaml  # pylint: disable=F0401
except ImportError:
  yaml = None


NonExistant = object()


SUPPORTED_SERIALIZERS = {'json', 'yaml'}
SERIALIZERS = {}


# JSON support
def re_encode(obj):
  if isinstance(obj, dict):
    return {re_encode(k): re_encode(v) for k, v in obj.iteritems()}
  elif isinstance(obj, list):
    return [re_encode(i) for i in obj]
  elif isinstance(obj, unicode):
    return obj.encode('utf-8')
  else:
    return obj


SERIALIZERS['json'] = (
    lambda s: re_encode(json.load(s)),
    lambda data, stream: json.dump(
        data, stream, sort_keys=True, indent=2, separators=(',', ': ')))


# YAML support
if yaml:
  _YAMLSafeLoader = getattr(yaml, 'CSafeLoader', yaml.SafeLoader)
  _YAMLSafeDumper = getattr(yaml, 'CSafeDumper', yaml.SafeDumper)
  SERIALIZERS['yaml'] = (
      lambda stream: yaml.load(stream, _YAMLSafeLoader),
      lambda data, stream: yaml.dump(
          data, stream, _YAMLSafeDumper, default_flow_style=False,
          encoding='utf-8'))


def GetCurrentData(test):
  """
  @type test: Test()
  @returns: The deserialized data (or NonExistant), and a boolean indicating if
            the current serialized data is in the same format which was
            requested by |test|.
  @rtype: (dict, bool)
  """
  for ext in sorted(SUPPORTED_SERIALIZERS, key=lambda s: s != test.ext):
    path = test.expect_path(ext)
    if ext not in SERIALIZERS and ext == test.ext:
      raise Exception('The package to support %s is not installed.' % ext)
    if os.path.exists(path):
      with open(path, 'rb') as f:
        data = SERIALIZERS[ext][0](f)
      return data, ext == test.ext
  return NonExistant, True


def WriteNewData(test, data):
  """
  @type test: Test()
  """
  if test.ext not in SUPPORTED_SERIALIZERS:
    raise Exception('%s is not a supported serializer.' % test.ext)
  if test.ext not in SERIALIZERS:
    raise Exception('The package to support %s is not installed.' % test.ext)
  with open(test.expect_path(), 'wb') as f:
    SERIALIZERS[test.ext][1](data, f)


def DiffData(old, new):
  """
  Takes old data and new data, then returns a textual diff as a list of lines.
  @type old: dict
  @type new: dict
  @rtype: [str]
  """
  if old is NonExistant:
    return new
  if old == new:
    return None
  else:
    return list(difflib.context_diff(
        pprint.pformat(old).splitlines(),
        pprint.pformat(new).splitlines(),
        fromfile='expected', tofile='current',
        n=4, lineterm=''
    ))
