#!/usr/bin/env python3
import os
from tornado import options as opts
import tokit


def main():
    opts.define('host', default='::1')
    opts.define('port', default='9091')
    opts.define('env', default=None)
    opts.parse_command_line()

    config = tokit.Config(__file__)
    config.set_env(opts.options.env)

    tokit.start(opts.options.host, opts.options.port, config)

if __name__ == '__main__':
    main()
