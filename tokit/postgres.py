import logging
import shortuuid
import uuid

import momoko
from psycopg2.extras import DictCursor
from psycopg2.extras import DictRow
import psycopg2.extensions

from tornado.gen import coroutine
from sqlbuilder.smartsql import Table, Query

import tokit
from tokit import api

logger = tokit.logger

class DictLogCursor(DictCursor):

    def execute(self, sql, args=None):
        logger.debug('Excute SQL: %s', self.mogrify(sql, args).decode())
        return super().execute(sql, args)


@tokit.on('init')
def pg_init(app):
    """ Hook to init Postgres momoko driver.
    dsn config is required, with syntax same as Psycopg2 DSN.

    Sample env.ini::

        [postgres]
        dsn=dbname=[APP_NAME]
        size=2
    """
    logging.getLogger('momoko').setLevel(logger.getEffectiveLevel())
    env = app.config.env['postgres']
    momoko_opts = dict(
        dsn=env['dsn'],
        size=int(env['size']),
        max_size=int(env['max_size']),
        auto_shrink=env.getboolean('auto_shrink'),
        cursor_factory=(DictLogCursor if env.getboolean('log') else DictCursor),
        # connection_factory=env.get('connection_factory', None),
    )
    app.pg_db = momoko.Pool(**momoko_opts)
    app.pg_db.connect()


class PgMixin:

    DbIntegrityError = psycopg2.IntegrityError
    DbError = psycopg2.Error

    @property
    def db(self):
        return self.application.pg_db

    @coroutine
    def pg_insert(self, table, fields=None, **data):
        """
        Postgres shorcut to insert data
        :return int new row's id

        Example::

            user_id = yield self.pg_insert('users', {"username": "foo", "password": "secret"})
        """
        if fields:
            data = self.get_request_dict(*fields)
        else:
            fields = list(data.keys())
        assert len(data) > 0  # check data
        values = list(data.values())

        sql = 'INSERT INTO {} ({}) VALUES ({}) RETURNING id ' \
            .format(table,
                    ','.join(fields),
                    ','.join(['%s'] * len(fields))
                    )
        cursor = yield self.db.execute(sql, values)
        return cursor.fetchone()[0]

    @coroutine
    def pg_update(self, table, data):
        changes = [field + ' = %s' for field in data.keys()]
        sql = 'UPDATE {} SET {} WHERE id = %s'.format(table, ','.join(changes))
        values = list(data.values()) + [data['id']]
        yield self.db.execute(sql, values)

    @coroutine
    def pg_query(self, query, *params):
        """ Low level execuation """
        result = yield self.db.execute(query, params)
        return result

    def pg_serialize(self, row):
        if not row:
            return
        ret = dict(row) if isinstance(row, DictRow) else row
        return ret

    @coroutine
    def pg_select(self, query, *params):
        """ Query and convert result """
        result = yield self.pg_query(query, *params)
        return [self.pg_serialize(row) for row in result.fetchall()]

    @coroutine
    def pg_one(self, query, *params):
        result = yield self.pg_query(query, *params)
        row = result.fetchone()
        if row:
            return self.pg_serialize(row)

    db_insert = pg_insert
    db_update = pg_update
    db_query = pg_query
    db_select = pg_select
    db_one = pg_one


class UidMixin:

    def pg_serialize(self, row):
        ret = PgMixin.pg_serialize(self, row)
        if 'id' in ret:
            ret['short_id'] = shortuuid.encode(uuid.UUID(ret['id']))
        return ret
