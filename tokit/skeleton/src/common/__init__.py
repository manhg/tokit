import tokit

from tokit.pg import PgMixin
from tokit.api import ErrorMixin, JsonMixin


class Config(tokit.Config):
    timezone = 'Asia/Tokyo'


def _addition(config):
    config.settings.update({
        'static_path': 'static'
    })


tokit.Event.get('config').attach(_addition)


class Websocket(ErrorMixin, tokit.Websocket):
    _repo_ = 'Request'


class Request(JsonMixin, PgMixin, ErrorMixin, tokit.Request):
    _repo_ = 'Request'

    def css(self):
        return ['style.css']

    def js(self):
        return ['vendor/riot+compiler.js', 'global.js']
