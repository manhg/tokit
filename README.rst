Recommended layout::

    ── fabfile.py
    └── src
        ├── app.py
        ├── common
        │   └── __init__.py
        ├── layout.html
        ├── some_module
        │   ├── __init__.py
        │   ├── template.html
        │   └── list.html
        ├── requirements.txt
        └── static
            ├── robots.txt
            ├── style.css
            └── vendor
                └── xyz.js

Usage::

    # app.py
    import tokit

    config = tokit.Config(__file__)
    if __name__ == '__main__':
        tokit.start(8000, config)

    # common/__init__.py
    import tokit
    import tornado.websocket
    
    from tokit.pg import PgMixin
    from tokit.api import parse_json, ErrorMixin, JsonMixin
    
    # Add events to bootstrap process
    def _addition(config):
        config.settings.update({
            'static_path': 'static'
        })
    
    tokit.Event.get('config').attach(_addition)
    
    class Websocket(ErrorMixin, tokit.Websocket):

        _repo_ = 'Request'
    
    # Per directory per module by default, let's say, put this class
    # in home/__init__.py
    class HomeHandler(Request):

        # Declare route inside the module
        _route_ = '^/$', 'home'

        def get(self):
            self.render('home.html')
