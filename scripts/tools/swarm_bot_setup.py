#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Setup a given bot to become a swarm bot by installing the
required files and setting up any required scripts. The bot's OS must be
specified. We assume the bot already has python installed and a ssh server
enabled."""

import optparse
import os
import subprocess
import sys

SWARM_DIRECTORY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    'swarm_bootstrap')

# The swarm server links.
SWARM_SERVER_PROD = 'https://chromium-swarm.appspot.com'
SWARM_SERVER_DEV = 'https://chromium-swarm-dev.appspot.com'

# The initial location of the swarm code on windows.
SWARM_WINDOWS_STARTING_DIRECTORY = 'c:\\b\\swarm_slave'

# The sftp destination for swarm files.
SFTP_SWARM_DIRECTORY = '/b/swarm_slave'

# The directories to store the swarm code.
SWARM_DIRECTORY = {
  'linux': SFTP_SWARM_DIRECTORY,
  'mac': SFTP_SWARM_DIRECTORY,
  'win': 'e:\\b\\swarm_slave\\',
}


class Options(object):
  def __init__(self, swarm_server):
    self.swarm_server = swarm_server


def CopySetupFiles(user, host, platform, options):
  sftp_stdin = [
      'rmdir %s' % SFTP_SWARM_DIRECTORY,
      'mkdir %s' % SFTP_SWARM_DIRECTORY,
      'put swarm_bootstrap/* %s' % SFTP_SWARM_DIRECTORY,
      'exit',
      ]

  return ['sftp', user + '@' + host], '\n'.join(sftp_stdin)


def OpenSSHCommand(user, host):
  return ['ssh', '-o ConnectTimeout=5', '-t', user + '@' + host]


def BuildSetupCommand(user, host, platform, options):
  assert platform in ('linux', 'mac', 'win')
  bot_setup_commands = []

  # On Windows the swarm files need to be moved to the correct directory.
  # This is because sftp can't access the e drive when copying the files over.
  if platform == 'win':
    bot_setup_commands.extend([
        'e:', '&&',
        'xcopy /i /e /h /y %s %s' % (SWARM_WINDOWS_STARTING_DIRECTORY,
                                     SWARM_DIRECTORY[platform]),
        '&&'])

  # Download and setup the swarm code from the server.
  bot_setup_commands.extend(['cd %s' % SWARM_DIRECTORY[platform], '&&'])
  bot_setup_commands.extend(['python', 'get_swarm_code.py',
                             options.swarm_server, '&&'])

  # Run the final swarm setup script.
  if platform == 'win':
    bot_setup_commands.extend([
        'call swarm_bot_setup.bat %s %s' %
        (options.swarm_server, SWARM_DIRECTORY[platform])])
  else:
    bot_setup_commands.append('./swarm_bot_setup.sh %s %s' %
                              (options.swarm_server, SWARM_DIRECTORY[platform]))

  # On windows the command must be executed by cmd.exe
  if platform == 'win':
    bot_setup_commands = ['cmd.exe /c',
                          '"' + ' '.join(bot_setup_commands) + '"']

  return OpenSSHCommand(user, host) + bot_setup_commands, ''


def BuildCleanCommand(user, host, platform):
  assert platform in ('linux', 'mac', 'win')

  command = OpenSSHCommand(user, host)
  if platform == 'win':
    command.append('del /q /s %s' % SWARM_DIRECTORY[platform])
  else:
    command.append('rm -f -r %s' % SWARM_DIRECTORY[platform])

  return command, ''


def main():
  parser = optparse.OptionParser(usage='%prog [options]',
                                 description=sys.modules[__name__].__doc__)
  parser.add_option('-b', '--bot', action='append', default=[],
                    help='The bot to setup as a swarm bot')
  parser.add_option('-r', '--raw',
                    help='The name of a file containing line separated slaves '
                    'to setup. The slaves must all be the same os.')
  parser.add_option('-c', '--clean', action='store_true',
                    help='Removes any old swarm files before setting '
                    'up the bot.')
  parser.add_option('-d', '--use_dev', action='store_true',
                    help='Set when the swarm bots being setup should use the '
                    'development swarm server instead of the production one.')
  parser.add_option('-u', '--user', default='chrome-bot',
                    help='The user to use when setting up the machine. '
                    'Defaults to %default')
  parser.add_option('-p', '--print_only', action='store_true',
                    help='Print what command would be executed to setup the '
                    'swarm bot.')
  parser.add_option('-w', '--win', action='store_true')
  parser.add_option('-l', '--linux', action='store_true')
  parser.add_option('-m', '--mac', action='store_true')


  options, args = parser.parse_args()

  if len(args) > 0:
    parser.error('Unknown arguments, ' + str(args))
  if not options.bot and not options.raw:
    parser.error('Must specify a bot or bot file.')
  if len([x for x in [options.win, options.linux, options.mac] if x]) != 1:
    parser.error('Must specify the bot\'s OS.')

  if options.win:
    platform = 'win'
  elif options.linux:
    platform = 'linux'
  elif options.mac:
    platform = 'mac'

  bots = options.bot
  if options.raw:
    # Remove extra spaces and empty lines.
    bots.extend(filter(None, (s.strip() for s in open(options.raw, 'r'))))

  for bot in bots:
    commands = []

    if options.clean:
      commands.append(BuildCleanCommand(options.user, bot, platform))

    command_options = Options(
        swarm_server=SWARM_SERVER_DEV if options.use_dev else SWARM_SERVER_PROD)

    commands.append(CopySetupFiles(options.user, bot, platform,
                                   command_options))
    commands.append(BuildSetupCommand(options.user, bot, platform,
                                      command_options))

    if options.print_only:
      print commands
    else:
      for command, stdin in commands:
        process = subprocess.Popen(command, stdin=subprocess.PIPE)
        process.communicate(stdin)

        if process.returncode:
          print 'Failed to execute command %s' % command
          return 1


if __name__ == '__main__':
  sys.exit(main())
