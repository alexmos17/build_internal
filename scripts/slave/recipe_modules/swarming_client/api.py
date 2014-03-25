# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api


class SwarmingClientApi(recipe_api.RecipeApi):
  """Code that both isolate and swarming recipe modules depend on.

  Both swarming and isolate scripts live in a single repository called
  'swarming client'. This module include common functionality like finding
  existing swarming client checkout, fetching a new one, getting version of
  a swarming script, etc.
  """

  def __init__(self, **kwargs):
    super(SwarmingClientApi, self).__init__(**kwargs)
    self._client_path = None
    self._script_version = {}

  def checkout(self, revision=None):
    """Returns a step to checkout swarming client into a separate directory.

    Ordinarily swarming client is checked out via Chromium DEPS into
    src/tools/swarming_client. This step configures recipe module to use
    a separate checkout.

    If |revision| is None, this requires the build property
    'parent_got_swarming_client_revision' to be present, and raises an exception
    otherwise. Fail-fast behavior is used because if machines silently fell back
    to checking out the entire workspace, that would cause dramatic increases
    in cycle time if a misconfiguration were made and it were no longer possible
    for the bot to check out swarming_client separately.
    """
    # If the following line throws an exception, it either means the
    # bot is misconfigured, or, if you're testing locally, that you
    # need to pass in some recent legal revision for this property.
    if revision is None:
      revision = self.m.properties['parent_got_swarming_client_revision']
    self._client_path = self.m.path['slave_build'].join('swarming.client')
    return self.m.git.checkout(
        url='https://chromium.googlesource.com/external/swarming.client.git',
        ref=revision,
        dir_path=self._client_path)

  @property
  def path(self):
    """Returns path to a swarming client checkout.

    It's subdirectory of Chromium src/ checkout or a separate directory if
    'checkout_swarming_client' step was used.
    """
    if self._client_path:
      return self._client_path
    # Default is swarming client path in chromium src/ checkout.
    # TODO(vadimsh): This line assumes the recipe is working with
    # Chromium checkout.
    return self.m.path['checkout'].join('tools', 'swarming_client')

  def query_script_version(self, script):
    """Returns a step to query a swarming script for its version.

    Version tuple later is accessible via 'get_script_version' method.
    """
    def followup_fn(step_result):
      version = step_result.stdout.strip()
      step_result.presentation.step_text = version
      step_result.presentation.step_summary_text = version
      self._script_version[script] = tuple(map(int, version.split('.')))
    return self.m.python(
        name='%s --version' % script,
        script=self.path.join(script),
        args=['--version'],
        stdout=self.m.raw_io.output(),
        followup_fn=followup_fn)

  def get_script_version(self, script):
    """Returns a version of some swarming script as a tuple (Major, Minor, Rev).

    It should have been queried by 'query_script_version' step before. Raises
    AssertionError if it wasn't.
    """
    assert script in self._script_version, script
    return self._script_version[script]