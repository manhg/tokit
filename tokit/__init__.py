#!/usr/bin/env python3
"""
@manhg/tokit

A kit for development with Tornado web framework.

See https://github.com/manhg/writekit for usage demo.
"""
version_info = (0, 1, 3, 0)
version = "0.1.3"
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

__all__ = ['MetaRepo', 'Repo', 'Request', 'Websocket', 'Module', 'Static', 'Config']

import re
import os
import collections
import logging
import time
import signal
import json
import importlib
import inspect
import configparser
from contextlib import contextmanager

import tornado.locale
import tornado.httpserver
import tornado.web
import tornado.websocket
from tornado.ioloop import IOLoop

def to_json(obj):
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


class Repo:
    """ Decorator-based registry of objects"""

    _repo = collections.defaultdict(list)

    def __init__(self, name=None):
        self.name = name

    def __call__(self, obj):
        if not self.name:
            if inspect.isclass(obj):
                parent_cls, *_ = inspect.getmro(obj)
                self.name = parent_cls.__name__
        self._repo[self.name].append(obj)
        return obj

    @classmethod
    def known(cls, name):
        """ Get registerd objects """
        return cls._repo.get(name, [])


class MetaRepo(type):
    """ A metaclass to make subclasses registry for any class """
    _repo = collections.defaultdict(list)

    def __init__(cls, name, bases, nmspc, **kwarg):
        # Instance object
        super(MetaRepo, cls).__init__(name, bases, nmspc)
        # Register
        repo_name = getattr(cls, '_repo_', None)
        if not repo_name:
            *_, base_cls = bases
            repo_name = base_cls.__name__
        MetaRepo._repo[repo_name].append(cls)

    @classmethod
    def known(mcs, parent_name) -> list:
        """ Get registered subclass of ``parent_name``
        :param str parent_name: pure class name without module prefix
        """
        return MetaRepo._repo[parent_name]


class Request(tornado.web.RequestHandler, metaclass=MetaRepo):
    """
    Base class for handling request
    Class hierarchy is defined right to left, methods are resolved is from left to right
    http://www.ianlewis.org/en/mixins-and-python
    Therefore, mixin if exists, should be added to the left of declare::

        class Foo(BarMixin, Request):
            pass
    """

    _route_ = None
    """
    Route can be pattern or (pattern, name) or an URLSpec::
    
        class Post(Request):
            _route_ = r'/post/.*'
            def get(self, slug):
                pass # Add logic here
    """

    def set_default_headers(self):
        self.set_header('Server', 'Python3')

    def abs_url(self, *args):
        return self.request.protocol + "://" + self.request.host + self.reverse_url(*args)

    def get_template_namespace(self):
        namespace = super(Request, self).get_template_namespace()
        namespace['json'] = to_json
        namespace['url'] = self.abs_url
        return namespace

    def js(self):
        """ List (to preserved ordering) of JS path to to used by layout file """
        return []

    def css(self):
        """ List (to preserved ordering) of CSS path to to used by layout file """
        return []

    def get_request_dict(self, *args):
        """ Return dict of request arguments """
        return collections.OrderedDict((field, self.get_body_argument(field)) for field in args)

    def redirect_referer(self):
        return self.redirect(self.request.headers.get('Referer', '/'))

    @property
    def env(self):
        return self.application.config.env

    @classmethod
    def known(cls):
        """ Get Request's subclasses """
        routes = []
        for handler in MetaRepo.known(cls.__name__):
            route = getattr(handler, '_route_', None)
            if not route:
                logging.debug("Missing route for handler %s.%s",
                    handler.__module__, handler.__name__)
                continue
            if isinstance(route, str):
                routes.append(tornado.web.URLSpec(route, handler))
            elif isinstance(route, tornado.web.URLSpec):
                routes.append(route)
            else:
                pattern, name = route
                routes.append(tornado.web.URLSpec(pattern, handler, name=name))
        return routes


class Websocket(tornado.websocket.WebSocketHandler, metaclass=MetaRepo):

    def reply(self, message=None, **kwargs):
        self.write_message(to_json(message or kwargs))


class Module(tornado.web.UIModule, metaclass=MetaRepo):
    """ Subclass this to create a UIModule
    It's available as class name::

        class Table(Module):
            def render(self):
                pass # then in template, you can use {% module Table() %}

    """

    @classmethod
    def known(cls):
        return {c.__name__: c for c in MetaRepo.known(cls.__name__)}


class Static(tornado.web.StaticFileHandler):
    
    ALLOW_TYPES = 'tag', 'js', 'css', 'png', 'jpg'
    VALID_PATH = re.compile(r'.*\.({types})$'.format(types='|'.join(ALLOW_TYPES)))

    def validate_absolute_path(self, root, absolute_path):
        """ Add file types checking """
        if not self.VALID_PATH.match(absolute_path):
            raise tornado.web.HTTPError(403, 'Unallowed file type')
        return absolute_path

class Event:
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
    in_production = False
    timezone = 'UTC'
    locale = 'en'
    modules = ()
    kill_blocking = 2  # (second) time to kill process if blocking too long
    session_timeout = 60 * 24 * 3600
    env_name = None
    env = {}

    def __init__(self, base_file):
        self.root_path = os.path.abspath(os.path.dirname(base_file))
        tornado.locale.load_translations('lang')

    def load(self, cfg_files=None):
        """ Load extra env config
        :param: list cfg_files relative path to project root
        """
        self.env = configparser.ConfigParser()
        main, *overrides = [os.path.join(self.root_path, f) for f in cfg_files]
        self.env.read_file(open(main))
        if len(overrides):
            self.env.read(overrides)
        
        self.in_production = self.env['app'].getboolean('in_production')
        log_level = self.env['app'].get('log_level')
        logging.basicConfig(level=getattr(logging, log_level))
        self.settings['cookie_secret'] = self.env['secret'].get('cookie_secret')

        Event.get('env').emit(self.env)


class App(tornado.web.Application):

    config = None


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
    Event.get('config').emit(config)
    config.settings['ui_modules'] = Module.known()
    app = App(**config.settings)
    app.config = config
    http_server = tornado.httpserver.HTTPServer(app, xheaders=True)
    ioloop = IOLoop.instance()
    Event.get('init').emit(app, ioloop)
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
    logging.info('Running PID {pid} @ localhost:{port}'.format(pid=os.getpid(), port=port))
    if config.in_production:
        # Automatically kill if anything blocks the process
        signal.signal(signal.SIGTERM, _on_term)
        ioloop.set_blocking_log_threshold(1)
        ioloop.set_blocking_signal_threshold(config.kill_blocking, action=None)
    try:
        ioloop.start()
    except KeyboardInterrupt:
        logging.info('Bye.')
