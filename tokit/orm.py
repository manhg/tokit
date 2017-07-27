import logging
import asyncio

import peewee
import peewee_async
from tornado.ioloop import IOLoop

import tokit

logger = tokit.logger
db_proxy = peewee.Proxy()
objects = peewee_async.Manager(db_proxy, loop=asyncio.get_event_loop())


class Model(peewee.Model):

    # see http://docs.peewee-orm.com/en/latest/peewee/database.html#dynamically-defining-a-database
    class Meta:
        database = db_proxy


def peewee_init(config):
    """
    Sample env.ini::

        [orm]
        driver=PostgresqlDatabase
        dbname=
    """
    env = config.env['orm']
    db_class = getattr(peewee_async, env.get('driver') or 'PostgresqlDatabase')
    db = db_class(
        env.get('dbname'),
        user=env.get('user'),
        password=env.get('password')
    )
    db_proxy.initialize(db)

tokit.Event.get('config').attach(peewee_init)