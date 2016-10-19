from time import time
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

class cached_property(object):
    """
    A property that is only computed once per instance and then replaces itself
    with an ordinary attribute. Deleting the attribute resets the property.
    Source: https://github.com/bottlepy/bottle/commit/fa7733e075da0d790d809aa3d2f53071897e6f76
    """  # noqa

    def __init__(self, func):
        self.__doc__ = getattr(func, '__doc__')
        self.func = func

    def __get__(self, obj, cls):
        if obj is None:
            return self
        value = obj.__dict__[self.func.__name__] = self.func(obj)
        return value

class cached_property_ttl(object):
    """
    A property that is only computed once per instance and then replaces itself
    with an ordinary attribute. Setting the ttl to a number expresses how long
    the property will last before being timed out.
    Source: https://github.com/pydanny/cached-property/blob/master/cached_property.py
    """

    def __init__(self, ttl=None):
        if callable(ttl):
            func = ttl
            ttl = None
        else:
            func = None
        self.ttl = ttl
        self._prepare_func(func)

    def __call__(self, func):
        self._prepare_func(func)
        return self

    def __get__(self, obj, cls):
        if obj is None:
            return self

        now = time()
        obj_dict = obj.__dict__
        name = self.__name__
        try:
            value, last_updated = obj_dict[name]
        except KeyError:
            pass
        else:
            ttl_expired = self.ttl and self.ttl < now - last_updated
            if not ttl_expired:
                return value

        value = self.func(obj)
        obj_dict[name] = (value, now)
        return value

    def __delete__(self, obj):
        obj.__dict__.pop(self.__name__, None)

    def __set__(self, obj, value):
        obj.__dict__[self.__name__] = (value, time())

    def _prepare_func(self, func):
        self.func = func
        if func:
            self.__doc__ = func.__doc__
            self.__name__ = func.__name__
            self.__module__ = func.__module__
