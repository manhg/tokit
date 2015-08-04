import logging
from tornado.gen import coroutine
import momoko

logger = logging.getLogger(__name__)

import tokit


def pg_init(app):
    """ Hook to init Postgres momoko driver.
    dsn config is required, with syntax same as Psycopg2 DSN.
    
    Sample env.ini::
    
        [postgres]
        dsn=dbname=[APP_NAME]
        size=2
    """
    postgres = app.config.env['postgres']
    app.db = momoko.Pool(dsn=postgres.get('dsn'), size=postgres.getint('size'))
    app.db.connect()


def pg_debug(_):
    for lg in [logger, logging.getLogger('momoko')]:
        lg.setLevel(logging.DEBUG)


tokit.Event.get('debug').attach(pg_debug)
tokit.Event.get('init').attach(pg_init)


class PgMixin:
    @property
    def db(self):
        """
        :return: momoko.Pool
        """
        return self.application.db

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
        cursor = yield self.db.execute(sql, values)
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
        yield self.db.execute(sql, values)
