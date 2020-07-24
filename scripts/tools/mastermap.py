#!/usr/bin/env python
# Copyright (c) 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tool for viewing mains, their hosts and their ports.

Has two main modes:
  a) In normal mode, simply prints the list of all known mains, sorted by
     hostname, along with their associated ports, for the perusal of the user.
  b) In --audit mode, tests to make sure that no mains conflict/overlap on
     ports (even on different mains) and that no mains have unexpected
     ports (i.e. differences of more than 100 between main, subordinate, and alt).
     Audit mode returns non-zero error code if conflicts are found. In audit
     mode, --verbose causes it to print human-readable output as well.

In both modes, --csv causes the output (if any) to be formatted as
comma-separated values.
"""

import json
import optparse
import os
import sys

# Should be <snip>/build/scripts/tools
SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))
BASE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, os.pardir, os.pardir))
sys.path.insert(0, os.path.join(BASE_DIR, 'scripts'))
sys.path.insert(0, os.path.join(BASE_DIR, 'site_config'))

import config_bootstrap
from subordinate import bootstrap

# These are ports likely to be running on a developer's machine, which may break
# presubmit tests.
PORT_BLACKLIST = set([
    8000,  # SimpleHTTPServer, dev_appserver.py
    8080,  # dev_appserver.py
    8088,  # goma
    8103,  # sshd
    8224,  # google-specific
])

def get_args():
  """Process command-line arguments."""
  parser = optparse.OptionParser(
      description='Tool to list all mains along with their hosts and ports.')

  parser.add_option('-l', '--list', action='store_true', default=False,
                    help='Output a list of all ports in use by all mains. '
                         'Default behavior if no other options are given.')
  parser.add_option('--sort-by', action='store',
                    help='Define the primary key by which rows are sorted. '
                    'Possible values are: "port", "alt_port", "subordinate_port", '
                    '"host", and "name". Only one value is allowed (for now).')
  parser.add_option('--find', action='store', type='int', default=0,
                    metavar='N',
                    help='Output N sets of three available ports.')
  parser.add_option('--audit', action='store_true', default=False,
                    help='Output conflict diagnostics and return an error '
                         'code if misconfigurations are found.')
  parser.add_option('--presubmit', action='store_true', default=False,
                    help='The same as --audit, but prints no output. '
                         'Overrides all other options.')

  parser.add_option('--csv', action='store_true', default=False,
                    help='Print output in comma-separated values format.')
  parser.add_option('--json', action='store_true', default=False,
                    help='Print output in JSON format. Overrides --csv.')
  parser.add_option('--full-host-names', action='store_true', default=False,
                    help='Refrain from truncating the main host names')

  opts, _ = parser.parse_args()

  opts.verbose = True

  if not (opts.find or opts.audit or opts.presubmit):
    opts.list = True

  if opts.presubmit:
    opts.list = False
    opts.audit = True
    opts.find = False
    opts.verbose = False

  return opts


def getint(string):
  """Try to parse an int (port number) from a string."""
  try:
    ret = int(string)
  except ValueError:
    ret = 0
  return ret


def human_print(lines, verbose):
  """Given a list of lists of tokens, pretty prints them in columns.

  Requires all lines to have the same number of tokens, as otherwise the desired
  behavior is not clearly defined (i.e. which columns should be left empty for
  shorter lines?).
  """

  for line in lines:
    assert len(line) == len(lines[0])

  num_cols = len(lines[0])
  format_string = ''
  for col in xrange(num_cols - 1):
    col_width = max(len(str(line[col])) for line in lines) + 1
    format_string += '%-' + str(col_width) + 's '
  format_string += '%s'

  if verbose:
    for line in lines:
      print(format_string % tuple(line))
    print('\n')


def csv_print(lines, verbose):
  """Given a list of lists of tokens, prints them as comma-separated values.

  Requires all lines to have the same number of tokens, as otherwise the desired
  behavior is not clearly defined (i.e. which columns should be left empty for
  shorter lines?).
  """

  for line in lines:
    assert len(line) == len(lines[0])

  if verbose:
    for line in lines:
      print(','.join(str(t) for t in line))
    print('\n')


def main_map(mains, output, opts):
  """Display a list of mains and their associated hosts and ports."""

  lines = [['Main', 'Config Dir', 'Host', 'Web port', 'Subordinate port',
            'Alt port', 'MSC', 'URL']]
  for main in mains:
    lines.append([
        main['name'], main['dirname'], main['host'], main['port'],
        main['subordinate_port'], main['alt_port'], main['msc'],
        main['buildbot_url']])

  output(lines, opts.verbose)


def main_audit(mains, output, opts):
  """Check for port conflicts and misconfigurations on mains.

  Outputs lists of mains whose ports conflict and who have misconfigured
  ports. If any misconfigurations are found, returns a non-zero error code.
  """
  # Return value. Will be set to 1 the first time we see an error.
  ret = 0

  # Look for mains configured to use the same ports.
  web_ports = {}
  subordinate_ports = {}
  alt_ports = {}
  all_ports = {}
  for main in mains:
    web_ports.setdefault(main['port'], []).append(main)
    subordinate_ports.setdefault(main['subordinate_port'], []).append(main)
    alt_ports.setdefault(main['alt_port'], []).append(main)

    for port_type in ('port', 'subordinate_port', 'alt_port'):
      all_ports.setdefault(main[port_type], []).append(main)

  # Check for blacklisted ports.
  lines = [['Blacklisted port', 'Main', 'Host']]
  for port, lst in all_ports.iteritems():
    if port in PORT_BLACKLIST:
      for m in lst:
        lines.append([port, m['name'], m['host']])
  output(lines, opts.verbose)

  # Check for conflicting web ports.
  lines = [['Web port', 'Main', 'Host']]
  for port, lst in web_ports.iteritems():
    if len(lst) > 1:
      ret = 1
      for m in lst:
        lines.append([port, m['name'], m['host']])
  output(lines, opts.verbose)

  # Check for conflicting subordinate ports.
  lines = [['Subordinate port', 'Main', 'Host']]
  for port, lst in subordinate_ports.iteritems():
    if len(lst) > 1:
      ret = 1
      for m in lst:
        lines.append([port, m['name'], m['host']])
  output(lines, opts.verbose)

  # Check for conflicting alt ports.
  lines = [['Alt port', 'Main', 'Host']]
  for port, lst in alt_ports.iteritems():
    if len(lst) > 1:
      ret = 1
      for m in lst:
        lines.append([port, m['name'], m['host']])
  output(lines, opts.verbose)

  # Look for mains whose port, subordinate_port, alt_port aren't separated by 100.
  lines = [['Main', 'Host', 'Web port', 'Subordinate port', 'Alt port']]
  for main in mains:
    if (getint(main['subordinate_port']) - getint(main['port']) != 100 or
        getint(main['alt_port']) - getint(main['subordinate_port']) != 100):
      ret = 1
      lines.append([main['name'], main['host'],
                   main['port'], main['subordinate_port'], main['alt_port']])
  output(lines, opts.verbose)

  return ret


def find_port(mains, output, opts):
  """Lists triplets of available ports for easy discoverability."""
  ports = set()
  for main in mains:
    for port in ('port', 'subordinate_port', 'alt_port'):
      ports.add(main[port])

  # Remove 0 from the set.
  ports = ports - {0}

  # Add blacklisted ports.
  ports = ports | PORT_BLACKLIST

  lines = [['Web port', 'Subordinate port', 'Alt port']]
  # In case we've hit saturation, search one past the end of the port list.
  for port in xrange(min(ports), max(ports) + 2):
    if (port not in ports and
        port + 100 not in ports and
        port + 200 not in ports):
      lines.append([port, port + 100, port + 200])
      if len(lines) > opts.find:
        break

  output(lines, opts.verbose)


def format_host_name(host):
  for suffix in ('.chromium.org', '.corp.google.com'):
    if host.endswith(suffix):
      return host[:-len(suffix)]
  return host


def extract_mains(mains):
  """Extracts the data we want from a collection of possibly-mains."""
  good_mains = []
  for main_name, main in mains.iteritems():
    if not hasattr(main, 'main_port'):
      # Not actually a main
      continue
    host = getattr(main, 'main_host', '')
    good_mains.append({
        'name': main_name,
        'host': host,
        'port': getattr(main, 'main_port', 0),
        'subordinate_port': getattr(main, 'subordinate_port', 0),
        'alt_port': getattr(main, 'main_port_alt', 0),
        'buildbot_url': getattr(main, 'buildbot_url', ''),
        'dirname': os.path.basename(getattr(main, 'local_config_path', ''))
    })
  return good_mains


def real_main(include_internal=False):
  opts = get_args()

  bootstrap.ImportMainConfigs(include_internal=include_internal)

  # These are the mains that are configured in site_config/.
  config_mains = extract_mains(
      config_bootstrap.config_private.Main.__dict__)
  for main in config_mains:
    main['msc'] = ''

  # These are the mains that have their own main_site_config.
  msc_mains = extract_mains(config_bootstrap.Main.__dict__)
  for main in msc_mains:
    main['msc'] = 'Y'

  # Define sorting order
  sort_keys = ['port', 'alt_port', 'subordinate_port', 'host', 'name']
  # Move key specified on command-line to the front of the list
  if opts.sort_by is not None:
    try:
      index = sort_keys.index(opts.sort_by)
    except ValueError:
      pass
    else:
      sort_keys.insert(0, sort_keys.pop(index))

  sorted_mains = config_mains + msc_mains
  for key in reversed(sort_keys):
    sorted_mains.sort(key = lambda m: m[key])

  if not opts.full_host_names:
    for main in sorted_mains:
      main['host'] = format_host_name(main['host'])

  if opts.csv:
    printer = csv_print
  else:
    printer = human_print

  if opts.list:
    if opts.json:
      print json.dumps(sorted_mains,
                       sort_keys=True, indent=2, separators=(',', ': '))
    else:
      main_map(sorted_mains, printer, opts)

  ret = 0
  if opts.audit or opts.presubmit:
    ret = main_audit(sorted_mains, printer, opts)

  if opts.find:
    find_port(sorted_mains, printer, opts)

  return ret


def main():
  return real_main(include_internal=False)


if __name__ == '__main__':
  sys.exit(main())
