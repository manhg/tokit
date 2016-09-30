"""
Transform to browsers' languages
Can serve files directly using shortcut: `python3 -m tokit.compiler`

Require system's libsass and pyv8
"""
import os
import io
import tornado.ioloop
import tornado.web
from tornado.iostream import IOStream
from tornado.gen import coroutine
from tornado.web import HTTPError
from tokit.tasks import ThreadPoolMixin, run_on_executor

COMPILER_URLS = []

def read_file(filename):
    with io.open(filename, encoding='utf8') as fp:
        return fp.read()


class CompilerHandler(ThreadPoolMixin, tornado.web.RequestHandler):

    def set_default_headers(self):
        self.set_header('Server', 'Python3')

    @coroutine
    def get(self, requested_file):
        try:
            requested_path = requested_file.replace(self.application.settings['static_url_prefix'], '/')
            full_path = self.application.root_path + requested_path
            if not os.path.exists(full_path):
                raise HTTPError(404)
            # TODO check harmful path
            yield self.compile(full_path)
        except Exception as e:
            self.set_status(400)
            self.write('/*')
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
    js_context = execjs.get().compile(
        read_file(os.path.dirname(__file__) + '/js/coffee-script.js')
    )
    riot_context = execjs.get().compile(
        read_file(os.path.dirname(__file__) + '/js/coffee-script.js') +
        ";\n\n var exports = {}; module.exports = {};" +  # fake CommonJS environment
        read_file(os.path.dirname(__file__) + '/js/riotc.js') + "; var riot = module.exports;"
    )

    class CoffeeHandler(CompilerHandler):

        def prepare(self):
            self.set_header('Content-Type', 'application/javascript')

        @run_on_executor
        def compile(self, full_path):
            result = js_context.call(
                "CoffeeScript.compile",
                read_file(full_path),
                {'bare': True}
            )
            self.write(result)

    class RiotHandler(CoffeeHandler):

        @run_on_executor
        def compile(self, full_path):
            result = riot_context.call(
                "riot.compile",
                read_file(full_path),
                True
            )
            self.write(result)


    COMPILER_URLS.append((r'^(/.+\.coffee)$', CoffeeHandler))
    COMPILER_URLS.append((r'^(/.+\.tag)$', RiotHandler))
except ImportError:
    pass

def init_complier(app):
    from tokit import logger
    if len(COMPILER_URLS):
        app.add_handlers('.*$', COMPILER_URLS)
        app.root_path = app.config.root_path
    else:
        logger.warn('Found no compilers handlers')

if __name__ == "__main__":
    app = tornado.web.Application(urlspecs())
    app.root_path = os.path.realpath(os.path.curdir)
    print("Serving via compiler in:", app.root_path)
    app.listen(7998)
    tornado.ioloop.IOLoop.current().start()
