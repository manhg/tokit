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
        return ['base.css', 'home/home.sass']

    def js(self):
        return ['riot.js', 'home/home.coffee', 'home/home.tag']
