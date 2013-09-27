# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api

class GSUtilApi(recipe_api.RecipeApi):
  def __call__(self, cmd, name=None, **kwargs):
    """A step to run arbitrary gsutil commands.

    Note that this assumes that gsutil authentication environment variables
    (AWS_CREDENTIAL_FILE and BOTO_CONFIG) are already set, though if you want to
    set them to something else you can always do so using the env={} kwarg.

    Note also that gsutil does its own wildcard processing, so wildcards are
    valid in file-like portions of the cmd. See 'gsutil help wildcards'.

    Arguments:
      cmd: list of (string) arguments to pass to gsutil.
           Include gsutil-level options first (see 'gsutil help options').
      name: the (string) name of the step to use.
            Defaults to the first non-flag token in the cmd.
    """
    if not name:
      name = (t for t in cmd if not t.startswith('-')).next()
    full_name = 'gsutil ' + name

    gsutil_path = self.m.path.depot_tools('third_party', 'gsutil', 'gsutil')

    return self.m.python(full_name, gsutil_path, cmd, **kwargs)

  def upload(self, source, bucket, dest, args=None, **kwargs):
    args = args or []
    full_dest = 'gs://%s/%s' % (bucket, dest)
    cmd = ['cp'] + args + [source, full_dest]
    name = kwargs.pop('name', 'upload')
    return self(cmd, name, **kwargs)

  def download(self, bucket, source, dest, args=None, **kwargs):
    args = args or []
    full_source = 'gs://%s/%s' % (bucket, source)
    cmd = ['cp'] + args + [full_source, dest]
    name = kwargs.pop('name', 'download')
    return self(cmd, name, **kwargs)
