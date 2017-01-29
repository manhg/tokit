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
import logging

COMPILER_URLS = []
logger = logging.getLogger('tokit')

def read_file(filename):
    with io.open(filename, encoding='utf8') as fp:
        return fp.read()


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

try:
    import sass

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
except ImportError:
    pass

try:
    import execjs

    lib_path = os.path.dirname(__file__) + '/js/'

    js_context = execjs.get().compile(read_file(lib_path + 'coffee-script.js'))
    babel_context = execjs.get().compile(read_file(lib_path + 'babel.js'))

    # source: https://raw.githubusercontent.com/stylus/stylus-lang.com/gh-pages/try/stylus.min.js
    stylus_context = execjs.get().compile(read_file(lib_path + 'stylus.js'))

    riot_context = execjs.get().compile(
        read_file(lib_path + 'coffee-script.js') +

        # HACK fake CommonJS environment to load the compiler
        # the library originally target NodeJS
        "var exports = {}; module.exports = {};" +
        read_file(lib_path + 'riot-compiler.js') + "; var riot = module.exports;" +

        # Riot custom language
        read_file(lib_path + 'stylus.js') +
        'riot.parsers.css.stylus = function(tagName, css) { return stylus.render(css) };'
    )

    class JavascriptHandler(CompilerHandler):

        def prepare(self):
            self.set_header('Content-Type', 'application/javascript')

    class CoffeeHandler(JavascriptHandler):

        @run_on_executor
        def compile(self, full_path):
            result = js_context.call(
                "CoffeeScript.compile",
                read_file(full_path),
                {'bare': True}
            )
            self.write(result)

    class StylusHandler(JavascriptHandler):

        def prepare(self):
            self.set_header('Content-Type', 'text/css')

        @run_on_executor
        def compile(self, full_path):
            # TODO add context to Stylus to utilize mixins and imports
            # http://stylus-lang.com/docs/import.html#javascript-import-api
            #   .set('filename', __dirname + '/test.styl')
            #   .set('paths', paths)
            result = stylus_context.call('stylus.render', read_file(full_path))
            self.write(result)

    class RiotHandler(JavascriptHandler):

        @run_on_executor
        def compile(self, full_path):
            result = riot_context.call(
                "riot.compile",
                read_file(full_path),
                True
            )
            self.write(result)

    class JsxHandler(JavascriptHandler):
    
        @run_on_executor
        def compile(self, full_path):
            result = babel_context.call('(global.Babel || module.exports).transform', read_file(full_path), {
                "plugins": ["transform-react-jsx"]
            })
            self.write(result)

    COMPILER_URLS.append((r'^(/.+\.styl)$', StylusHandler))
    COMPILER_URLS.append((r'^(/.+\.coffee)$', CoffeeHandler))
    COMPILER_URLS.append((r'^(/.+\.tag)$', RiotHandler))
    COMPILER_URLS.append((r'^(/.+\.jsx)$', JsxHandler))
except ImportError:
    pass
    

def init_complier(app):
    from tokit import logger
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
    print("Serving via compiler in:", app.root_path)
    app.listen(opts.options.port, opts.options.host)
    tornado.ioloop.IOLoop.current().start()

if __name__ == "__main__":
    main()