import logging

from tornado.gen import coroutine
import momoko
from sqlbuilder.smartsql import Table, Query

import tokit

logger = tokit.logger


def pg_init(app):
    """ Hook to init Postgres momoko driver.
    dsn config is required, with syntax same as Psycopg2 DSN.

    Sample env.ini::

        [postgres]
        dsn=dbname=[APP_NAME]
        size=2
    """
    logging.getLogger('momoko').setLevel(logger.getEffectiveLevel())
    postgres = app.config.env['postgres']
    app.pg_db = momoko.Pool(dsn=postgres.get('dsn'), size=postgres.getint('size'))
    app.pg_db.connect()

tokit.Event.get('init').attach(pg_init)


class PgMixin:

    @property
    def db(self):
        return self.pg_db()

    def pg_db(self):
        """
        :return: momoko.Pool
        """
        return self.application.pg_db

    @coroutine
    def pg_insert(self, table, fields=None, **data):
        """
        Postgres shorcut to insert data

        Example::

            user_id = yield self.pg_insert('users', {"username": "foo", "password": "secret"})

        .. warning::
            Must decorate caller method with ``tornado.gen.coroutine`` because this is async

        :return int row's id
        """
        if fields:
            data = list(self.get_request_dict(*fields).values())
        else:
            fields = list(data.keys())
            values = list(data.values())
        assert len(data) > 0  # check data

        sql = 'INSERT INTO {} ({}) VALUES ({}) RETURNING id ' \
            .format(table,
                    ','.join(fields),
                    ','.join(['%s'] * len(fields))
                    )
        cursor = yield self.pg_db().execute(sql, values)
        return cursor.fetchone()[0]

    @coroutine
    def pg_update(self, table, row_id, data):
        """
        Postgres shorcut to update data.

        .. warning::
            Must decorate callee with ``tornado.gen.coroutine`` because this is async

        """
        changes = [field + ' = %s' for field in data.keys()]
        sql = 'UPDATE {} SET {} WHERE id = %s'.format(table, ','.join(changes))
        values = list(data.values())
        values.append(row_id)
        yield self.pg_db().execute(sql, values)

    @coroutine
    def pg_query(self, statement):
        """
        statement - a tuple (sql, params) or a sqlbuilder.Query instance
        """
        query = statement
        if isinstance(query, Query):
            query = statement.select()
        yield self.pg_db().execute(*query)

    def db_prepare(self, row_id=None):
        t = getattr(Table, table)
        q = Query(t)
        if row_id:
            q.where(t.id == row_id)
        return t, q

    db_insert = pg_insert
    db_update = pg_update
    db_query = pg_query
