from tokit import Request
from tokit.utils import on
from tokit.compiler import init_complier

@on('init')
def setup(app):
    init_complier(app)

class Home(Request):

    URL = '/'

    def get(self):
        self.render('home.html')

    def css(self):
        return ['base.css', 'home/home.sass']

    def js(self):
        return ['riot.js', 'home/home.coffee', 'home/home.tag']
