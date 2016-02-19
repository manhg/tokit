"""
Tranform to languages of browsers.
Can serve files directly using shortcut: `python3 -m tokit.compiler`

Require libsass and pyv8
"""
import os
import tornado.ioloop
import tornado.web
from tornado.iostream import IOStream

import coffeescript
import sass


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


class CoffeeHandler(CompilerHandler):

    def prepare(self):
        self.set_header('Content-Type', 'application/javascript')

    def compile(self, requested_file):
        self.write(
            coffeescript.compile_file(self.application.root_path + requested_file)
        )


class SassHandler(CompilerHandler):

    def prepare(self):
        self.set_header('Content-Type', 'text/css')

    def compile(self, requested_file):
        self.write(sass.compile(
            filename=self.application.root_path + requested_file,
            output_style=('nested' if self.application.settings['debug'] else 'compressed')
        ))


def urlspecs():
    return [
        (r'^(/.+\.coffee)$', CoffeeHandler),
        (r'^(/.+\.sass)$', SassHandler),
    ]


def attach():
    def _complier(app):
        app.add_handlers('.*$', urlspecs())
        app.root_path = app.config.root_path

    import tokit
    tokit.Event.get('init').attach(_complier)

if __name__ == "__main__":
    app = tornado.web.Application(urlspecs())
    app.root_path = os.path.realpath(os.path.curdir)
    print("Serving via compiler in:", app.root_path)
    app.listen(7998)
    tornado.ioloop.IOLoop.current().start()
