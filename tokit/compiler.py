"""
Transform to browsers' languages
Can serve files directly using shortcut: ``python3 -m tokit.compiler``

For Sass, it requires system's ``libsass`` installed.

For Coffeescript it need a Javascript runtime, either by
having Python's ``pyv8`` (with ``libv8`` installed or system's ``node``

For Stylus, it has same requirements as Coffeescript
"""
import os
import io
import tornado.ioloop
import tornado.web
from tornado.iostream import IOStream
from tornado.gen import coroutine
from tornado.web import HTTPError
from tokit.tasks import ThreadPoolMixin, run_on_executor
from tokit import ValidPathMixin
from tokit.utils import on
from tokit import logger

COMPILER_URLS = []


class CompilerHandler(ThreadPoolMixin, ValidPathMixin, tornado.web.RequestHandler):

    def set_default_headers(self):
        self.set_header('Cache-Control', "max-age: 2592000'")

    @coroutine
    def get(self, requested_file):
        requested_path = requested_file.replace(self.application.settings['static_url_prefix'], '')
        abs_path = os.path.abspath(os.path.join(self.application.root_path, requested_path))
        self.validate_absolute_path(self.application.root_path, abs_path)
        try:
            yield self.compile(abs_path)
        except Exception as e:
            self.set_status(400)
            logger.exception(e)

            if (self.settings['debug']):
                # /* */ are comment style supported by both Javascript and CSS
                self.write("/*\n")
                self.write(f"Handler: {self.__class__.__name__}\n")
                self.write(f"Exception while compiling {requested_file}\n\n")
                self.write(str(e))
                self.write('*/')

def init_complier(app):
    try:
        import execjs
        has_execjs = True
    except ImportError:
        has_execjs = False

    if has_execjs:
        from tokit.js import StylusHandler, CoffeeHandler, RiotHandler, JsxHandler
        COMPILER_URLS.append((r'^(/.+\.styl)$', StylusHandler))
        COMPILER_URLS.append((r'^(/.+\.coffee)$', CoffeeHandler))
        COMPILER_URLS.append((r'^(/.+\.tag)$', RiotHandler))
        COMPILER_URLS.append((r'^(/.+\.jsx)$', JsxHandler))
    
    try:
        import sass
        has_sass = True
    except ImportError:
        has_sass = False

    if has_sass:
        class SassHandler(CompilerHandler):
    
            def prepare(self):
                self.set_header('Content-Type', 'text/css')
    
            @run_on_executor
            def compile(self, full_path):
                result = sass.compile(
                    filename=full_path,
                    output_style=('nested' if self.application.settings['debug'] else 'compressed')
                )
                self.write(result)
    
        COMPILER_URLS.append((r'^(/.+\.sass)$', SassHandler))
    
    if len(COMPILER_URLS):
        app.add_handlers('.*$', COMPILER_URLS)
        app.root_path = app.config.root_path
    else:
        logger.warn('Found no compilers handlers')

def main():
    from tornado import options as opts

    opts.define('host', default='::1')
    opts.define('port', default='80')
    opts.parse_command_line()

    app = tornado.web.Application(urlspecs())
    app.root_path = os.path.realpath(os.path.curdir)
    print(f"Serving via compiler in: {app.root_path}")
    print(f"URL: {opts.options.port}:{opts.options.host}")
    app.listen(opts.options.port, opts.options.host)
    tornado.ioloop.IOLoop.current().start()

if __name__ == "__main__":
    main()