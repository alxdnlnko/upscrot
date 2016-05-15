#!/usr/bin/env python3

# Directly upload screenshot to sftp server
# Author: Danilo Bargen
# License: GPLv3

import collections
import configparser
import datetime
import os
import subprocess
import sys
import tempfile
import webbrowser
import sys

import appdirs


def init_config():
    """
    Initialize config.

    If config file exists, read it.
    If not, initialize it.

    """
    confdir = appdirs.user_config_dir('upscrot')
    try:
        os.makedirs(confdir)
    except FileExistsError:
        pass
    confpath = os.path.join(confdir, 'config.ini')

    # Initialize configparser
    config = configparser.ConfigParser(dict_type=collections.OrderedDict)

    # Read config file if it exists
    if os.path.exists(confpath):
        config.read(confpath)
        return config

    # Create it otherwise.
    else:
        config['local'] = {
            '# save_to': '/home/user/pictures/',
            'file_prefix': 'screenshot-',
            'file_permissions': '0644'
        }
        config['upload'] = {
            'target_host': 'example.org',
            'target_dir': '/var/www/tmp/screenshots',
            'base_url': 'https://example.org/tmp/screenshots/',
            '# open_in_browser': 1
        }
        with open(confpath, 'w+') as f:
            config.write(f)
        print('Created initial config file.')
        print('Please edit \'%s\' and then run upscrot again.' % confpath)
        sys.exit(1)


def main(config):
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    prefix = config.get('local', 'file_prefix', fallback='screenshot-')

    save_to = config.get('local', 'save_to', fallback=None)
    screenshot = tempfile.NamedTemporaryFile(
            dir=save_to,
            prefix='%s%s-' % (prefix, timestamp),
            suffix='.png'
    )
    filename = screenshot.name

    if save_to:
        # close tempfile to allow scrot to recreate it
        screenshot.close()

    # Take screenshot
    try:
        subprocess.check_call(['scrot', '-s', filename], stdout=subprocess.DEVNULL)
    except subprocess.CalledProcessError as e:
        print('Could not take screenshot: %s' % e)
        exit(-1)

    # Set permissions
    mode = config.get('local', 'file_permissions', fallback='0644')
    os.chmod(filename, int(mode, base=8))

    # Upload file
    # ensure config includes all needed options
    options = set(['target_host', 'target_dir', 'base_url'])
    if config.has_section('upload') and len((options & config['upload'].keys())) >= len(options):
        try:
            subprocess.check_call([
                'scp',
                filename,
                '%s:%s' % (config.get('upload', 'target_host'), config.get('upload', 'target_dir')),
            ], stdout=subprocess.DEVNULL)
        except subprocess.CalledProcessError as e:
            print('Could not copy file to server: %s' % e)
            exit(-1)
        url = config.get('upload', 'base_url') + os.path.basename(filename)

        # X clipboard
        try:
            clipboards = ['-pi', '-bi']
            for clipboard in clipboards:
                xsel = subprocess.Popen(['xsel', clipboard], stdin=subprocess.PIPE)
                xsel.communicate(input=url.encode('utf8'))
        except OSError:
            pass

        # Open in browser
        if config.get('upload', 'open_in_browser', fallback=False):
            webbrowser.open(url, autoraise=False)

        try:
            print(url, flush=True)
        except (BrokenPipeError, IOError):
            pass

    sys.stderr.close()


def entrypoint():
    config = init_config()
    main(config)


if __name__ == '__main__':
    entrypoint()
