import logging
import os
from uuid import UUID

import shortuuid
import cassandra
from cassandra.cluster import Cluster
from cassandra.cqlengine import connection as cqlengine_connection
from cassandra.query import dict_factory
from tornado.concurrent import Future
from tornado.ioloop import IOLoop

import tokit

logger = logging.getLogger(__name__)


def allow_management():
    os.environ['CQLENG_ALLOW_SCHEMA_MANAGEMENT'] = 'CQLENG_ALLOW_SCHEMA_MANAGEMENT'


def cassandra_init(app):
    """
    Sample configuration::

        [cassandra]
        contact_points=
            host1
            host2
        port=9042
        keyspace=blabla
    """
    logging.getLogger('cs').setLevel(tokit.logger.getEffectiveLevel())
    try:
        config = app.config.env['cassandra']
    except KeyError:
        logger.warn('Cassandra was not configured')
        return
    hosts = [p.strip() for p in config.get('contact_points').strip().split('\n')]
    logger.debug('%s', hosts)

    # for use with controllers
    cluster = Cluster(
        contact_points=hosts,
        port=int(config.get('port')),
        connect_timeout=1,
    )
    keyspace = app.config.env['cassandra'].get('keyspace')
    session = cluster.connect(keyspace)
    session.row_factory = dict_factory
    app.cs_pool = session
    
    # for use with object mapper
    cqlengine_connection.setup(
        hosts,
        default_keyspace=config.get('keyspace'),
        lazy_connect=True, retry_connect=True
    )
    # Further hook
    tokit.Event.get('cassandra_init').emit(app)


tokit.Event.get('init').attach(cassandra_init)

def serialize(row):
    if 'id' in row:
        row['short_id'] = shortuuid.encode(row['id'])
    return row


class IntegrityError(BaseException):
    """ this never happen because row will be overrided """
    pass


class CassandraMixin:
    """
    Reference: http://datastax.github.io/python-driver/api/cassandra/cluster.html#cassandra.cluster.Session.execute_async
    """

    DbIntegrityError = IntegrityError
    DbError = cassandra.RequestExecutionException

    @property
    def cs_pool(self):
        return self.application.cs_pool

    def cs_query(self, cql, *args):
        future = Future()
        cs_future = self.cs_pool.execute_async(cql, args)

        def _success(result):
            IOLoop.instance().add_callback(future.set_result, result)

        def _fail(e):
            IOLoop.instance().add_callback(future.set_exception, e)

        cs_future.add_callbacks(_success, _fail)
        return future

    async def cs_one(self, table, row_id):
        result = await self.cs_query(
            "SELECT * FROM " + table + " WHERE id = %s ",
            row_id
        )
        if result:
            return serialize(result[0])

    async def cs_upsert(self, table, **data):
        id = data.get('id', UUID())
        cql = "UPDATE {table} SET ".format(table=table) + ", ".join([
            k + " = %s " for k in data.keys()
        ]) + "WHERE id = %s"
        result = await self.cs_query(cql, list(data.values()) + [data['id']])
        return result

    async def cs_insert(self, table, **data):
        fields = data.keys()
        cql = 'INSERT INTO {} ({}) VALUES ({})'.format(table,
            ','.join(fields),
            ','.join(['%s'] * len(fields))
        )
        result = await self.cs_query(cql, *list(data.values()))
        return result

    db_insert = cs_upsert
    db_update = cs_upsert
    db_one = cs_one
