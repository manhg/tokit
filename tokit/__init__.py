#!/usr/bin/env python3
"""
@manhgd/tokit
A kit for development with Tornado web framework.
"""

__all__ = ['MetaRepo', 'Repo', 'Request', 'Websocket', 'Module', 'Static', 'Config']

import os, sys, subprocess
import re
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
import tornado.netutil
from tornado.ioloop import IOLoop

logger = logging.getLogger('tokit')


def to_json(obj):
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


class Repo:
    """ Decorator-based registry of objects

    Example::

    """

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
        """ Get registered objects
        :return: list
        """
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
        return collections.OrderedDict(
            (field, self.get_body_argument(field, None)) for field in args)

    def redirect_referer(self):
        return self.redirect(self.request.headers.get('Referer', '/'))

    @property
    def env(self):
        return self.application.config.env

    @classmethod
    def known(cls):
        """ Get Request's subclasses
        TODO add weight or ordering important routes
        """
        routes = []
        for handler in MetaRepo.known(cls.__name__):
            route = getattr(handler, '_route_', None)
            if not route:
                logger.debug("Missing route for handler %s.%s",
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
    def reply(self, _payload=None, **kwargs):
        self.write_message(_payload or to_json(kwargs))

    @property
    def env(self):
        return self.application.config.env


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
    ALLOW_TYPES = 'tag', 'js', 'css', 'png', 'jpg', 'txt'
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


class AttributeDict(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


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
    x = AttributeDict()
    root_path = None
    in_production = False
    timezone = 'UTC'
    locale = 'en'

    modules = None
    """ List of dirname, as a module """

    kill_blocking = 2
    """ (second) time to kill process if blocking too long """

    session_timeout = 60 * 24 * 3600
    env_name = None
    env = {}

    def __init__(self, base_file):
        self.root_path = os.path.abspath(os.path.dirname(base_file))
        self.settings['static_path'] = os.path.join(self.root_path, self.settings['static_path'])
        lang_path = os.path.join(self.root_path, 'lang')
        if os.path.exists(lang_path):
            tornado.locale.load_translations(lang_path)

    def load(self, cfg_files=None):
        """ Load extra env config
        :param: list cfg_files relative path to project root
        """
        self.env = configparser.ConfigParser()
        main, *overrides = [os.path.join(self.root_path, f) for f in cfg_files]
        self.env.read_file(open(main))
        if len(overrides):
            self.env.read(overrides)

        Event.get('env').emit(self.env)
        self.setup()
        Event.get('config').emit(self)

    def setup(self):
        self.in_production = self.env['app'].getboolean('in_production')
        self.settings['debug'] = self.env['app'].getboolean('debug')
        log_level = self.env['app'].get('log_level')
        logging.basicConfig(level=getattr(logging, log_level))
        self.settings['cookie_secret'] = self.env['secret'].get('cookie_secret')
        dns_resolver = self.env['app'].get('dns_resolver', 'tornado.netutil.ThreadedResolver')
        tornado.netutil.Resolver.configure(dns_resolver)


class App(tornado.web.Application):
    config = None

    @classmethod
    def instance(cls, config):
        load(config)
        Event.get('config').emit(config)
        config.settings['ui_modules'] = Module.known()
        app = App(**config.settings)
        app.config = config
        Event.get('init').emit(app)
        Event.get(config.env_name).emit(app)
        app.add_handlers('.*$', Request.known())
        return app


def load(config):
    """ Import declared modules from config, during this imports, routes
    and other components will be registered """
    os.environ['TZ'] = config.timezone
    time.tzset()
    tornado.locale.set_default_locale(config.locale)
    if not config.modules:
        # Search all modules as a dir,
        _, config.modules, _ = next(os.walk(config.root_path))
        # Exclude special dirnames
        config.modules = [m for m in config.modules \
                          if not (m.startswith('.') or m.startswith('_'))]
    loaded = []
    for m in config.modules:
        try:
            importlib.import_module(m)
            loaded.append(m)
        except TypeError:
            pass
        except SyntaxError:
            ex = sys.exc_info()
            logger.error("Broken module: %s %s %s", ex[0].__name__,
                         os.path.basename(
                             sys.exc_info()[2].tb_frame.f_code.co_filename),
                         ex[2].tb_lineno)
            sys.exit(1)
    logger.info('Autoloaded modules: %s', loaded)


def start(port, config):
    """ Entry point for application. This setups IOLoop, load classes and run HTTP server """
    app = App.instance(config)

    http_server = tornado.httpserver.HTTPServer(app, xheaders=True)
    ioloop = IOLoop.instance()

    def _graceful():
        def _shutdown():
            pass

        ioloop.stop()
        logger.info('Shutting down...')
        http_server.stop()
        ioloop.call_later(1, _shutdown)

    def _on_term(*args):
        ioloop.add_callback_from_signal(_graceful)

    http_server.listen(port, 'localhost')
    logger.info('Running PID {pid} @ localhost:{port}'.format(pid=os.getpid(), port=port))
    if config.in_production:
        # Automatically kill if anything blocks the process
        signal.signal(signal.SIGTERM, _on_term)
        ioloop.set_blocking_log_threshold(1)
        ioloop.set_blocking_signal_threshold(config.kill_blocking, action=None)
    try:
        Event.get('start').emit(app)
        ioloop.start()
    except KeyboardInterrupt:
        logger.info('Bye.')
