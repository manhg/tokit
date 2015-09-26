from _app import Request

class HomeHandler(Request):

    _route_ = '^/', 'home'

    def get(self):
        self.render('home.html')
