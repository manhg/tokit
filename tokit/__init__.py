#!/usr/bin/env python3
import os, sys, re, collections, logging
import time, signal, importlib, inspect, configparser
from contextlib import contextmanager

import tornado.locale
from tornado.httpserver import HTTPServer
import tornado.web
import tornado.websocket
import tornado.netutil
from tornado.ioloop import IOLoop
from tornado.autoreload import add_reload_hook
from tornado import testing

from tokit.utils import Event, on, to_json, make_rand

logger = logging.getLogger('tokit')


class Repo:
    """
    Decorator-based registry of objects
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


class Registry(type):
    """ A metaclass to make subclasses registry for any class """
    _repo = collections.defaultdict(list)

    def __init__(cls, name, bases, nmspc, **kwarg):
        # Instance object
        super(Registry, cls).__init__(name, bases, nmspc)
        # Register
        repo_name = getattr(cls, 'REPO', None)
        if not repo_name:
            *_, base_cls = bases
            repo_name = base_cls.__name__
        if cls.__name__ == repo_name:
            # Don't add itself, the abstract repo class
            return
        Registry._repo[repo_name].append(cls)

    @classmethod
    def known(mcs, parent_name) -> list:
        """ Get registered subclass of ``parent_name``
        :param str parent_name: pure class name without module prefix
        """
        return Registry._repo[parent_name]


class Request(tornado.web.RequestHandler, metaclass=Registry):
    """
    Base class for handling request
    Class hierarchy is defined right to left, methods are resolved is from left to right
    http://www.ianlewis.org/en/mixins-and-python
    Therefore, mixin if exists, should be added to the left of declare::

        class Foo(BarMixin, Request):
            pass
    """

    URL = None
    """
    Route can be pattern or (pattern, name) or an URLSpec::

        class Post(Request):
            URL = r'/post/.*'
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
        """
        Return dict of request arguments, use with standard HTTP form
         """
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
        for handler in Registry.known(cls.__name__):
            route = getattr(handler, 'URL', None)
            if not route:
                if not handler.__module__.startswith('_'):
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


class Websocket(tornado.websocket.WebSocketHandler, metaclass=Registry):
    def reply(self, _payload=None, **kwargs):
        self.write_message(_payload or to_json(kwargs))

    @property
    def env(self):
        return self.application.config.env


class Module(tornado.web.UIModule, metaclass=Registry):
    """ Subclass this to create a UIModule
    It's available as class name::

        class Table(Module):
            def render(self):
                pass # then in template, you can use {% module Table() %}

    """

    @classmethod
    def known(cls):
        return {c.__name__: c for c in Registry.known(cls.__name__)}


class Assets(tornado.web.StaticFileHandler):
    ALLOW_TYPES = (
        'tag', 'js', 'css',
        'png', 'jpg', 'ico', 'svg', 'gif',
        'zip', 'tar', 'tgz', 'txt'
    )
    VALID_PATH = re.compile(r'.*\.({types})$'.format(types='|'.join(ALLOW_TYPES)))

    def validate_absolute_path(self, root, absolute_path):
        """ Add file types checking """
        if not self.VALID_PATH.match(absolute_path):
            raise tornado.web.HTTPError(403, 'Unallowed file type')
        return absolute_path

    @classmethod
    def get_content_version(cls, abspath):
        return super().get_content_version(abspath)[:6]

class Config:
    """ Subclass this to customize runtime config """

    settings = dict(
        static_path='.',
        static_url_prefix='/static/',
        static_handler_class=Assets
    )
    root_path = None
    graceful = True
    timezone = 'UTC'

    modules = None
    """ List of dirname, as a module """

    """ (second) time to kill process if blocking too long """
    env_name = None
    env = {}

    def __init__(self, base_file):
        self.root_path = os.path.abspath(os.path.dirname(base_file))
        os.chdir(self.root_path)
        self.settings['static_path'] = os.path.join(self.root_path, self.settings['static_path'])

    def read_ini(self, cfg_files=None):
        """ Load extra env config
        :param: list cfg_files relative path to project root
        """
        main, *overrides = [os.path.join(self.root_path, '../config', f) for f in cfg_files]
        self.env.read_file(open(main))
        if len(overrides):
            self.env.read(overrides)

    def setup(self):
        self.graceful = self.env['app'].getboolean('graceful')
        boolenv = self.env['app'].getboolean
        self.settings['debug'] = boolenv('debug')
        self.settings['compiled_template_cache'] = boolenv('compiled_template_cache', self.settings['debug'])
        self.settings['static_hash_cache'] = boolenv('static_hash_cache', self.settings['debug'])
        self.settings['compress_response'] = boolenv('compress_response', True)
        self.settings['cookie_secret'] = self.env['secret'].get('cookie_secret', make_rand())

        log_level = getattr(logging, self.env['app'].get('log_level'))
        logging.basicConfig(level=log_level)
        logger.setLevel(log_level)

        dns_resolver = self.env['app'].get('dns_resolver', 'tornado.netutil.ThreadedResolver')
        tornado.netutil.Resolver.configure(dns_resolver)

        os.environ['TZ'] = self.timezone
        time.tzset()
        
        locale_name = self.env['app'].get('locale', 'en')
        tornado.locale.set_default_locale(locale_name)

    def set_env(self, env_name=None):
        self.env = configparser.ConfigParser()
        self.env_name = env_name or os.environ.get('ENV', 'development')
        self.read_ini(['base.ini', self.env_name + '.ini'])
        logging.info('Env: ' + self.env_name)
        Event.get('env').emit(self.env)
        self.setup()
        Event.get('config').emit(self)

    def load_modules(self):
        """
        Import declared modules from config, during this imports, routes
        and other components will be registered
        """
        if not self.modules:
            # Search all modules as a dir,
            _, self.modules, _ = next(os.walk(self.root_path))
            # Exclude special dirnames
            self.modules = [
                m for m in self.modules
                if not (m.startswith('.') or m.startswith('_'))
            ]
        loaded = []
        for m in self.modules:
            try:
                importlib.import_module(m)
                loaded.append(m)
            except SyntaxError as e:
                ex = sys.exc_info()
                logger.error("Broken module: %s %s %s", ex[0].__name__,
                             os.path.basename(
                                 sys.exc_info()[2].tb_frame.f_code.co_filename),
                             ex[2].tb_lineno)
                raise e
        self.modules_loaded = loaded

class App(tornado.web.Application):
    config = None

    @classmethod
    def instance(cls, config):
        config.load_modules()
        Event.get('config').emit(config)
        config.settings['ui_modules'] = Module.known()

        app = App(**config.settings)
        app.config = config
        Event.get('init').emit(app)
        Event.get(config.env_name).emit(app)

        app.add_handlers('.*$', Request.known())
        Event.get('after_init').emit(app)
        return app

def start(host, port, config):
    """
    Entry point for application.
    This setups IOLoop, load classes and run HTTP server
    """

    app = App.instance(config)

    http_server = HTTPServer(app, xheaders=True)
    ioloop = IOLoop.instance()
    http_server.listen(port, host)
    logger.info('Running PID {pid} @ http://{host}:{port}'.format(host=host, pid=os.getpid(), port=port))
    
    def _reload():
        """ reload Python code should also clear cache """
        Assets.reset()
        with Request._template_loader_lock:
            for loader in Request._template_loaders.values():
                loader.reset()
    
    add_reload_hook(_reload)

    if config.graceful:
        def _graceful():
            """
            Schedule shutdown on next tick
            """
            def _shutdown():
                http_server.stop()
                ioloop.stop()
                logger.info('Stopped')

            ioloop.call_later(1, _shutdown)

        def _on_term(*args):
            ioloop.add_callback_from_signal(_graceful)

        # Automatically kill if anything blocks the process
        signal.signal(signal.SIGTERM, _on_term)
        signal.signal(signal.SIGINT, _on_term)
        ioloop.set_blocking_log_threshold(1)
        time_to_kill = config['env']['app'].get('kill_blocking_sec', 2)
        ioloop.set_blocking_signal_threshold(time_to_kill, action=None)

    try:
        Event.get('start').emit(app)
        ioloop.start()
    except KeyboardInterrupt:
        logger.info('Bye.')
    except Exception as e:
        logger.exception(e)
        logger.info('Server was down.')
