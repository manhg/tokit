from tokit import Request
from tokit.utils import on
from tokit.compiler import init_complier
from tokit.translation import init_locale, TranslationMixin

@on('init')
def init(app):
    init_complier(app)
    init_locale(app.config)

class Home(TranslationMixin, Request):

    URL = '/'

    def get(self):
        self.render('home.html')

    def css(self):
        yield 'base.css'
        yield 'home/home.sass'

    def js(self):
        yield from ['riot.js', 'home/home.coffee', 'home/home.tag']


class About(TranslationMixin, Request):

    URL = '/about', 'about'

    def get(self):
        self.render('about.jade')
        
    def css(self):
        yield 'base.css'
