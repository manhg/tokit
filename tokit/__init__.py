#!/usr/bin/env python3
"""
@manhg/tokit

A kit for development with Tornado web framework.

See https://github.com/manhg/writekit for usage demo.
"""
version_info = (0, 1, 1, 0)
version = "0.1.1"
import os, sys, subprocess

if __name__ == '__main__':
    # TODO Create project structure, dependancies
    print("Project installation: ", os.getcwd())
    if not input("Press Enter to continue, N to exit: "):
        print("Writing: ")
    [os.makedirs(p) for p in ("static", "src/vendor")]
    subprocess.call(
        "pyvenv . ;"
        "source bin/activate;"
        "pip3 install tornado;"
        , stderr=subprocess.STDOUT, shell=True)
    sys.exit(0)

__all__ = ['Register', 'Request', 'Websocket', 'Module', 'Static', 'Config']

import re
import collections
import logging
import time
import signal
import json
import importlib
from contextlib import contextmanager

import tornado.locale
import tornado.httpserver
import tornado.web
import tornado.websocket
from tornado.ioloop import IOLoop


def to_json(obj):
    return json.dumps(obj, ensure_ascii=False, indent=4)


class Register(type):
    """ A metaclass to log information of all subclasses """
    _repo = collections.defaultdict(list)

    def __init__(cls, name, bases, nmspc, **kwarg):
        Register._repo[bases[0].__name__].append(cls)
        super(Register, cls).__init__(name, bases, nmspc)

    @classmethod
    def collect(mcs, parent_name) -> list:
        """ Get all subclass of ``parent_name``

        parent_name -- str pure class name without module prefix
        """
        return Register._repo[parent_name]


class Request(tornado.web.RequestHandler, metaclass=Register):
    """ Base class for handling request """

    ROUTE = None
    """
    Route can be pattern or (pattern, name) or an URLSpec::
    
        class Post(Request):
            ROUTE = r'/post/.*'
            def get(self, slug):
                pass # Add logic here
    """

    def set_default_headers(self):
        self.set_header('Server', 'Python3')

    def get_template_namespace(self):
        namespace = super(Request, self).get_template_namespace()
        namespace['json'] = to_json
        return namespace

    def js(self):
        """ List (to preserved ordering) of JS path to to used by layout file """
        return []

    def css(self):
        """ List (to preserved ordering) of CSS path to to used by layout file """
        return []

    @classmethod
    def known(cls):
        """ Get Request's subclasses """
        routes = []
        for handler in Register.collect(cls.__name__):
            if not handler.ROUTE:
                logging.debug("Missing route for handler %s.%s",
                    handler.__module__, handler.__name__)
                continue
            if isinstance(handler.ROUTE, str):
                routes.append(tornado.web.URLSpec(handler.ROUTE, handler))
            elif isinstance(handler.ROUTE, tornado.web.URLSpec):
                routes.append(handler.ROUTE)
            else:
                pattern, name = handler.ROUTE
                routes.append(tornado.web.URLSpec(pattern, handler, name=name))
        return routes


class Websocket(tornado.websocket.WebSocketHandler, metaclass=Register):
    pass


class Module(tornado.web.UIModule, metaclass=Register):
    """ Subclass this to create a UIModule
    It's available as class name::

        class Table(Module):
            def render(self):
                pass # then in template, you can use {% module Table() %}

    """

    @classmethod
    def known(cls):
        return {c.__name__: c for c in Register.collect(cls.__name__)}


class Static(tornado.web.StaticFileHandler):
    
    ALLOW_TYPES = 'tag', 'js', 'css', 'png', 'jpg'
    VALID_PATH = re.compile(r'.*\.({types})$'.format(types='|'.join(ALLOW_TYPES)))

    def validate_absolute_path(self, root, absolute_path):
        """ Add file types checking """
        if not self.VALID_PATH.match(absolute_path):
            raise tornado.web.HTTPError(403, 'Unallowed file type')
        return absolute_path

class Event():
    """Event handlers storage.

    Example:

    >>> def handler(**kwargs):
    ...     print("Triggered:", kwargs)
    ...
    >>> Event.get('init').attach(handler)
    >>> Event.get('init').emit(status='OK')
    Triggered: {'status': 'OK'}

    """

    _repo = {}

    def __init__(self, name):
        self._handlers = set()
        self.name = name

    def attach(self, task):
        self._handlers.add(task)

    def detach(self, task):
        self._handlers.remove(task)

    @classmethod
    def get(cls, name):
        instance = cls._repo.get(name, None)
        if not instance:
            instance = cls(name)
            cls._repo[name] = instance
        return instance

    @contextmanager
    def subscribe(self, *tasks):
        for task in tasks:
            self.attach(task)
        try:
            yield
        finally:
            for task in tasks:
                self.detach(task)

    def emit(self, *args, **kwargs):
        for handler in self._handlers:
            handler(*args, **kwargs)


class Config:
    """ Subclass this to customize runtime config """
    
    settings = dict(
        compress_response=True,
        static_path='.',
        static_url_prefix='/static/',
        static_handler_class=Static,
        debug=True,
        compiled_template_cache=False,
        cookie_secret='TODO'
    )
    root_path = None
    production = False
    timezone = 'UTC'
    locale = 'en'
    modules = ()
    kill_blocking = 2  # (second) time to kill process if blocking too long
    session_timeout = 60 * 24 * 3600

    def __init__(self, base_file):
        self.root_path = os.path.abspath(os.path.dirname(base_file))
        tornado.locale.load_translations('lang')

    def dev(self):
        """ Expose debug """
        import tornado.options
        tornado.options.parse_command_line()
        logging.basicConfig(level=logging.DEBUG)

    def production(self):
        """ Common config for production """
        self.production = True
        logging.basicConfig(level=logging.WARNING)
        self.cookie_secret=os.environ.get('SECRET')


class App(tornado.web.Application):
    pass


def load(config):
    """ Import declared modules from config, during this imports, routes
    and other components will be registered """
    try:
        os.environ['TZ'] = config.timezone
        time.tzset()
        tornado.locale.set_default_locale(config.locale)
        for m in config.modules:
            importlib.import_module(m)
    except SyntaxError:
        ex = sys.exc_info()
        logging.error("Broken module: ", ex[0].__name__,
                      os.path.basename(
                          sys.exc_info()[2].tb_frame.f_code.co_filename),
                      ex[2].tb_lineno)
        sys.exit(1)


def start(port, config):
    """ Entry point for application. This setups IOLoop, load classes and run HTTP server """
    load(config)
    Event.get('setting').emit(config.settings)
    config.settings['ui_modules'] = Module.known()
    app = App(**config.settings)
    app.config = config
    http_server = tornado.httpserver.HTTPServer(app, xheaders=True)
    ioloop = IOLoop.instance()
    Event.get('init').emit(app)
    app.add_handlers('.*$', Request.known())

    def _graceful():
        def _shutdown():
            pass

        ioloop.stop()
        logging.info('Shutting down...')
        http_server.stop()
        ioloop.call_later(1, _shutdown)

    def _on_term(*args):
        ioloop.add_callback_from_signal(_graceful)

    http_server.listen(port, 'localhost')
    signal.signal(signal.SIGTERM, _on_term)

    logging.info('Running PID {pid} @ localhost:{port}'.format(pid=os.getpid(), port=port))
    if config.production:
        ioloop.set_blocking_log_threshold(1)
        ioloop.set_blocking_signal_threshold(config.kill_blocking, action=None)
    try:
        ioloop.start()
    except KeyboardInterrupt:
        logging.info('Bye.')
