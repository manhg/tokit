#!/usr/env python3
import tokit
import os
import logging

import _app

from tornado.options import define, options, parse_command_line
define('port', default='7380')
define('env', default=None)
parse_command_line()

def get_config(env_name=None):
    config = _app.Config(__file__)
    os.chdir(config.root_path)
    config.env_name = options.env or env_name or os.environ.get('ENV', 'development')
    try:
        # Add common.ini if needed to share
        config.load(['../config/%s.ini' % config.env_name])
    except FileNotFoundError as e:
        logging.warning('Config file is not present')
    logging.info('Env: ' + config.env_name)    
    return config

if __name__ == '__main__':
    tokit.start(options.port, get_config())
