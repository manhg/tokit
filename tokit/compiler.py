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

COMPILER_URLS = []

def read_file(filename):
    with io.open(filename, encoding='utf8') as fp:
        return fp.read()


class CompilerHandler(tornado.web.RequestHandler):

    def set_default_headers(self):
        self.set_header('Server', 'Python3')

    def get(self, requested_file):
        try:
            self.compile(requested_file)
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

        def compile(self, requested_file):
            self.write(sass.compile(
                filename=self.application.root_path + requested_file,
                output_style=('nested' if self.application.settings['debug'] else 'compressed')
            ))

    COMPILER_URLS.append((r'^/static(/.+\.sass)$', SassHandler))
except ImportError:
    pass

try:
    import execjs

    class CoffeeHandler(CompilerHandler):

        def prepare(self):
            self.set_header('Content-Type', 'application/javascript')
            self.context = execjs.get().compile(
                read_file(os.path.dirname(__file__) + '/js/coffee-script.js')
            )

        def compile(self, requested_file):
            result = self.context.call(
                "CoffeeScript.compile",
                read_file(self.application.root_path + requested_file),
                {'bare': True}
            )
            self.write(result)

    class RiotHandler(CompilerHandler):

        def prepare(self):
            self.set_header('Content-Type', 'application/javascript')
            self.context = execjs.get().compile(
                read_file(os.path.dirname(__file__) + '/js/coffee-script.js') +
                ";\n\n var exports = {}; module.exports = {};" +  # fake CommonJS environment
                read_file(os.path.dirname(__file__) + '/js/riotc.js') + "; var riot = module.exports;"
            )

        def compile(self, requested_file):
            result = self.context.call(
                "riot.compile",
                read_file(self.application.root_path + requested_file),
                True
            )
            self.write(result)


    COMPILER_URLS.append((r'^/static(/.+\.coffee)$', CoffeeHandler))
    COMPILER_URLS.append((r'^/static(/.+\.tag)$', RiotHandler))
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
