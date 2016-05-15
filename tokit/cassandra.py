import logging
import os
from uuid import UUID

from cassandra.cluster import Cluster
from cassandra.cqlengine import connection as cqlengine_connection
from tornado.gen import coroutine
from tornado.concurrent import Future
from tornado.ioloop import IOLoop

import tokit
from sqlbuilder.smartsql import Table, Query, Result
from sqlbuilder.smartsql.compilers.cassandra import compile as cassandra_compile

logger = logging.getLogger(__name__)


def allow_management():
    os.environ['CQLENG_ALLOW_SCHEMA_MANAGEMENT'] = 'CQLENG_ALLOW_SCHEMA_MANAGEMENT'


def cassandra_init(app):
    """
    Sample configuration::

        [cassandra]
        contact_points=
            192.168.1.1
            192.168.1.2
        port=9042
        keyspace=blabla
    """
    logging.getLogger('cs').setLevel(tokit.logger.getEffectiveLevel())
    try:
        config = app.config.env['cassandra']
    except KeyError:
        logger.warn('Cassandra was not configured')
        return
    hosts = [p.strip() for p in config.get('contact_points').split('\n')]
    # For use with controller
    app.cassandra_cluster = Cluster(
        contact_points=hosts,
        port=int(config.get('port')),
        connect_timeout=1,
    )
    # For use with object mapper
    cqlengine_connection.setup(
        hosts,
        default_keyspace=config.get('keyspace'),
        lazy_connect=True, retry_connect=True
    )
    # Further hook
    tokit.Event.get('cassandra_init').emit(app)


tokit.Event.get('init').attach(cassandra_init)


def valid_id(row_id):
    try:
        return UUID(row_id)
    except ValueError:
        raise HTTPError(400, 'Invalid UUID')


def prepare(table, row_id=None):
    t = getattr(Table, table)
    q = Query(t, result=Result(compile=cassandra_compile))
    if row_id:
        q = q.where(t.id == valid_id(row_id))
    return t, q


class CassandraMixin:
    """
    Reference: http://datastax.github.io/python-driver/api/cassandra/cluster.html#cassandra.cluster.Session.execute_async
    """

    @property
    def db(self):
        return cs_db()

    def cs_db(self, keyspace=None):
        """
        Get Cassandra session
        TODO reuse session?
        """
        if not keyspace:
            keyspace = self.application.config.env['cassandra'].get('keyspace')
        return self.application.cassandra_cluster.connect(keyspace)

    def cs_insert(self, table, data):
        t, q = prepare(table)
        statement = q.insert(data)
        return self.cs_query(statement)

    def cs_update(self, table, row_id, data):
        _, q = prepare(table, row_id)
        statement = q.update(data)
        return self.cs_query(statement)

    def cs_delete(self, table_row_id):
        _, q = prepare(table, row_id)
        statement = q.delete()
        return self.cs_query(statement)

    def cs_query(self, statement):
        """
        statement - a tuple (sql, params) or a sqlbuilder.Query instance

        Reference: http://alexapps.net/cassandra-asynchronous-future-calls-pyth/
        """
        query = statement
        if isinstance(query, Query):
            query = statement.select()
        future = Future()
        logger.debug('Cassandra executes: %s', query)
        # Cassanra driver use a different thread
        cs_future = self.cs_db().execute_async(*query)

        def _success(result):
            IOLoop.instance().add_callback(future.set_result, result)

        def _fail(e):
            IOLoop.instance().add_callback(future.set_exception, e)

        cs_future.add_callbacks(_success, _fail)
        return future

    def db_prepare(self, table):
        return prepare(table)

    def db_row(self, table, row_id):
        t, q = prepare(table, row_id)
        statement = q.fields('*').select()
        return self.cs_query(statement)

    # Aliases
    db_insert = cs_insert
    db_update = cs_update
    db_query = cs_query
