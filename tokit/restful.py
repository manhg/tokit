import logging

from tornado.gen import coroutine
from sqlbuilder.smartsql import Table, Query

from tokit import MetaRepo, Request, logger, Event
from tokit.api import ErrorMixin, JsonMixin

class Resource(ErrorMixin, JsonMixin, Request):
    """
    This must be subclass and mix with a DB Mixin which supports
    `db_query, db_update, db_insert` methods

    To add checking, permission by roles
    Overide `def prepare(self)
    """

    _repo_ = 'Resource'
    _prefix_ = '/restful'
    _restful_ = None

    @coroutine
    def get(self): # list items
        t = Table(self._restful_)
        q = Query().tables(t).fields('*')
        rows = yield self.db_query(q)
        # TODO fix JSON serialize problem - unhashtable dict
        self.write({
            'length': len(rows),
            # 'items': tuple(rows)
        })

    def post(self):
        pass


class Item(ErrorMixin, JsonMixin, Request):
    _repo_ = 'Item'
    _prefix_ = '/restful'
    _restful_ = None

    def get(self, id):
        pass

    def patch(self, id):
        pass

    def delete(self, id):
        pass


def register_endpoints(self):
    # If accept-content is json, run the endpoint
    # If accept HTML then return reference documentation
    resources = MetaRepo.known('Resource')
    items = MetaRepo.known('Item')
    print(items)
    request_repo = MetaRepo._repo['Request']

    UUID_REGEX = '[\-a-zA-Z0-9]+'
    resource_items = {item._restful_ : item for item in items}

    for resource in resources:
        resource._route_ = r'^{prefix}/{res}/?$'.format(
            prefix=resource._prefix_,
            res=resource._restful_
        )
        request_repo.append(resource)
        item = resource_items.get(resource._restful_, None)
        # allow resources without item
        if item:
            item._route_ = r'^{prefix}/{res}/{id}/?$'.format(
                prefix=resource._prefix_,
                res=resource._restful_,
                id=UUID_REGEX)
            request_repo.append(item)

    
Event.get('init').attach(register_endpoints)
