import binascii
import hashlib
import json
from contextlib import contextmanager
from datetime import datetime
from json import JSONEncoder
from uuid import UUID
import shortuuid


class Event:
    """
    Event handlers storage.

    Example:

    >>> def handler(**kwargs):
    ...     print("Triggered:", kwargs)
    ...
    >>> Event.get('some_thing_happened').attach(handler)
    >>> Event.get('some_thing_happened').emit(status='OK')
    Triggered: {'status': 'OK'}

    """

    _repo = {}

    def __init__(self, name):
        self.handlers = []
        self.name = name

    def attach(self, handler, priority=0):
        handler._event_priority = priority
        self.handlers.append(handler)
        self.handlers.sort(key=lambda h: h._event_priority)

    def detach(self, handler):
        self.handlers.remove(handler)

    @classmethod
    def get(cls, name):
        instance = cls._repo.get(name, None)
        if not instance:
            instance = cls(name)
            cls._repo[name] = instance
        return instance

    @contextmanager
    def subscribe(self, *handlers):
        for handler in handlers:
            self.attach(handlers)
        try:
            yield
        finally:
            for handlers in handlers:
                self.detach(handlers)

    def emit(self, *args, **kwargs):
        for handler in self.handlers:
            handler(*args, **kwargs)


def on(event_name, priority=0):
    def decorator(fn):
        Event.get(event_name).attach(fn, priority)
    return decorator

class VersatileEncoder(JSONEncoder):
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
            return shortuuid.encode(obj)
        elif isinstance(obj, datetime):
            return str(obj)
        else:
            try:
                return JSONEncoder.default(self, obj)
            except TypeError:
                return str(obj)


def to_json(obj):
    return json.dumps(obj, ensure_ascii=False, cls=VersatileEncoder).replace("</", "<\\/")

def make_rand(length=16):
    shortuuid.ShortUUID().random(length)

def make_hash(secret, **kwargs):
    kwargs = kwargs or dict(
        salt=b'tokit',
        iterations=82016,
    )
    # might be GIL dependent
    dk = hashlib.pbkdf2_hmac('sha512', str.encode(secret), **kwargs)
    return binascii.hexlify(dk).decode()

try:
    import markdown


    def md_html(raw):
        """
        Convert Markdown format string to HTML
        WARNING: Be careful of leading spaces
        """
        html = markdown.markdown(raw.decode())
        return html
except:
    pass
