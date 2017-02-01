import os
import io
import execjs

from tokit import logger
from tokit.tasks import run_on_executor
from tokit.compiler import CompilerHandler

class JavascriptHandler(CompilerHandler):

    @property
    def js_library_path(self):
        try:
            env = self.application.config.env['compiler']
            return env['js_library_path']
        except KeyError:
            return os.path.dirname(__file__)

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