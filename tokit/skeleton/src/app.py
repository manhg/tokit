#!/usr/env python3
import common
import tokit
import os
import logging

from tornado.options import define, options, parse_command_line
define('port', default='7380')
define('env', default=None)
parse_command_line()


def get_config(env_name=None):
    config = common.Config(__file__)
    config.env_name = options.env or env_name or os.environ.get('ENV', 'development')
    config.load(['../config/%s.ini' % config.env_name])
    logging.info('Env: ' + config.env_name)    
    return config

if __name__ == '__main__':
    tokit.start(options.port, get_config())
