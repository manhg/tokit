from tokit import Request

class Strict(Request):

    def set_default_headers(self):
        super().set_default_headers()

        # this mean no inline script, css
        # and restrict all resources to current domain
        self.set_header('Content-Security-Policy',
            "default-src 'self';"
        )