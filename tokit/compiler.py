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
import logging

COMPILER_URLS = []
logger = logging.getLogger('tokit')


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

    class JavascriptHandler(CompilerHandler):
    
        @property
        def js_library_path(self):
            try:
                env = self.application.config.env['compiler']
                return env['js_library_path']
            except KeyError:
                return os.path.dirname(__file__) + '/js/'
            
        def read_file(self, filename):
            full_path = os.path.join(self.js_library_path, filename)
            with io.open(full_path, encoding='utf8') as fp:
                return fp.read()

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.context = execjs.get().compile(self.read_file('coffee-script.js'))

        def prepare(self):
            self.set_header('Content-Type', 'application/javascript')

    class CoffeeHandler(JavascriptHandler):

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.context = execjs.get().compile(self.read_file('coffee-script.js'))

        @run_on_executor
        def compile(self, full_path):
            result = self.context.call(
                "CoffeeScript.compile",
                self.read_file(full_path),
                {'bare': True}
            )
            self.write(result)

    class StylusHandler(JavascriptHandler):
    
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.context = execjs.get().compile(self.read_file('stylus.js'))

        def prepare(self):
            self.set_header('Content-Type', 'text/css')

        @run_on_executor
        def compile(self, full_path):
            # TODO add context to Stylus to utilize mixins and imports
            # http://stylus-lang.com/docs/import.html#javascript-import-api
            #   .set('filename', __dirname + '/test.styl')
            #   .set('paths', paths)
            result = self.context.call('stylus.render', self.read_file(full_path))
            self.write(result)

    class RiotHandler(JavascriptHandler):

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # source: https://raw.githubusercontent.com/stylus/stylus-lang.com/gh-pages/try/stylus.min.js

            with io.StringIO() as buffer:
                buffer.write(self.read_file('coffee-script.js'))
                buffer.write(
                    # HACK fake CommonJS environment to load the compiler
                    # the library originally target NodeJS
                    "var exports = {}; module.exports = {};"
                )
                buffer.write(self.read_file('riot-compiler.js'))
                buffer.write("; var riot = module.exports;")

                # Riot custom language
                buffer.write(self.read_file('stylus.js'))
                buffer.write('riot.parsers.css.stylus = function(tagName, css) { return stylus.render(css) };')
                self.context = execjs.get().compile(buffer.getvalue())

        @run_on_executor
        def compile(self, full_path):
            if os.path.isdir(full_path):
                content = self.compile_folder(full_path)
            else:
                content = self.read_file(full_path)
            result = self.context.call(
                "riot.compile", content, True
            )
            self.write(result)

        def compile_folder(self, folder):
            """ support a folder composed of html, css, js and preprocessors """
            tag_name = os.path.basename(folder).strip('.tag')
            with io.StringIO() as buffer:
                buffer.write(f"<{tag_name}>\n")

                for f in os.listdir(folder):
                    if f.endswith('.styl'):
                        buffer.write('\n<style type="text/stylus">\n')
                        buffer.write(self.read_file(os.path.join(folder, f)))
                        buffer.write('\n</style>')

                    elif f.endswith('.html'):
                        buffer.write(self.read_file(os.path.join(folder, f)))

                    elif f.endswith('.coffee'):
                        buffer.write('\n<script type="coffee">\n')
                        buffer.write(self.read_file(os.path.join(folder, f)))
                        buffer.write('\n</script>')
                    else:
                        logger.warn(f"Unknown how to compile: {f}")

                buffer.write(f"\n</{tag_name}>")
                return buffer.getvalue()



    class JsxHandler(JavascriptHandler):
    
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.context = execjs.get().compile(self.read_file('babel.js'))

        @run_on_executor
        def compile(self, full_path):
            result = self.context.call('(global.Babel || module.exports).transform',
                self.read_file(full_path), {
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