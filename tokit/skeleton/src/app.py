#!/usr/env python3
import tokit
import os
import logging

import _app

from tornado.options import define, options, parse_command_line
define('port', default='7380')
define('env', default=None)
parse_command_line()

if __name__ == '__main__':
    config = _app.Config(__file__)
    config.set_env(options.env)
    tokit.start(options.port, config)
