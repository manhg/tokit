import sys
import hashlib
from base64 import b64encode

from tokit import Request

def sha256_base64(data):
    m = hashlib.sha256()
    m.update(data)
    return b64encode(m.digest())

def js_inline(code):
    hashed = sha256_base64(code)
    caller_locals = sys._getframe(2).f_locals
    print(caller_locals['self'])
    print(caller_locals.keys())
    handler.set_header('Content-Security-Policy',
            "default-src 'self';"
            f"script-src 'strict-dynamic' 'sha256-{hashed};"
    )
    return code

class Strict(Request):
    REPO = 'Request'

    TEMPLATE_NS = {
        'js_inline': js_inline
    }

    def set_default_headers(self):
        super().set_default_headers()

        # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Security-Policy/script-src

        # this mean no inline script, css
        # and restrict all resources to current domain
        self.set_header('Content-Security-Policy',
            "default-src 'self';"
        )


class Secured(Strict):

    URL = '/secured'

    def get(self):
        self.render('secured.html')
