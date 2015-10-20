import json
import traceback
import sys
import functools
import string
import random

import tokit

from tornado.websocket import WebSocketHandler

from json import JSONEncoder
from uuid import UUID


def secret(length=16):
    return ''.join(random.SystemRandom(). \
                   choice(string.ascii_uppercase + string.digits) \
                   for _ in range(length))


def parse_json(s):
    try:
        return json.loads(s)
    except ValueError as e:
        raise Exception('Invalid JSON: ' + str(e))


def api_auth(method):
    """
    Require auth cookie to access an API
    """

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        if not self.current_user:
            self.write_exception(Exception('Login required'))
        return method(self, *args, **kwargs)

    return wrapper


class FullEncoder(JSONEncoder):
    """
    Encode all "difficult" object such as UUID
    """

    def _iterencode(self, obj, markers=None):

        if isinstance(obj, tuple) and hasattr(obj, '_asdict'):
            gen = self._iterencode_dict(obj._asdict(), markers)
        else:
            gen = JSONEncoder._iterencode(self, obj, markers)
        for chunk in gen:
            yield chunk

    def default(self, obj):
        if isinstance(obj, UUID):
            return str(obj)
        else:
            return JSONEncoder.default(self, obj)


full_encoder = FullEncoder()


class JsonMixin:
    """ Auto parse JSON request body and store in self.data """

    def prepare(self):
        super().prepare()
        self.data = None
        if self.request.body:
            try:
                self.data = parse_json(self.request.body.decode())
            except ValueError as e:
                self.write_exception(e)

    def encode(self, obj=None, **kwargs):
        if isinstance(obj, list):
            raise ValueError('Lists not accepted for security reasons')
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        ret = kwargs if not obj else obj
        self.write(full_encoder.encode(ret))


class ErrorMixin:
    """ Show errors in JSON instead of default HTML

    Always check key "status" from result, will be "ok" or "error"
    """

    def write_exception(self, e):
        error_type = e.__class__.__name__
        if self.settings['debug']:
            self.write_error(error_type, exc_info=sys.exc_info())
        else:
            self.write_error(error_type, reason=str(e))

    def write_error(self, status_code, reason=None, **kwargs):
        response = {
            'status': 'error',
            'code': status_code,
        }
        if self.settings.get("serve_traceback") and "exc_info" in kwargs:
            response['detail'] = traceback.format_exception(*kwargs["exc_info"])
        else:
            response['reason'] = reason
        if isinstance(self, WebSocketHandler):
            self.write_message(response)
        else:
            self.write(response)
            self.finish()
