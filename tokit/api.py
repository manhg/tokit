import re
import json
import traceback
import functools
import string
import random
import cgitb
import logging


from tornado.websocket import WebSocketHandler
from tornado.gen import coroutine
from tornado.web import HTTPError

from cerberus import Validator

from tokit import Registry, Request, logger, on
from tokit.utils import to_json

SHORT_UUID_RE = '[\-a-zA-Z0-9]{22}'

def parse_json(s):
    try:
        return json.loads(s)
    except ValueError as e:
        raise Exception('Invalid JSON: ' + str(e))


class JsonMixin:
    """
    * Auto parse JSON request body and store in self.data
    * Support render whatever objects as JSON
    """

    def prepare(self):
        self.data = None
        if self.request.body:
            try:
                self.data = parse_json(self.request.body.decode())
            except ValueError as e:
                self.write_exception(e)

    def write_json(self, obj=None, **kwargs):
        if isinstance(obj, list):
            raise ValueError('Lists not accepted for security reasons')
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        ret = kwargs if not obj else obj
        self.write(to_json(ret))


class ErrorMixin:
    """
    Show errors in JSON instead of default HTML

    Always check key "status" from result, will be "ok" or "error"
    """

    def write_error(self, status_code, **kwargs):
        response = {}
        if 'exc_info' in kwargs:
            cls, exception, tb = kwargs['exc_info']
            if hasattr(exception, 'reason'):
                response['reason'] = exception.reason
            if hasattr(exception, 'detail'):
                response['detail'] = exception.detail
        self.set_status(status_code)
        if isinstance(self, WebSocketHandler):
            self.write_message(response)
        else:
            self.write(response)
            self.finish()


class Resource(ErrorMixin, JsonMixin, Request):
    """
    This provides quickway to build an API around a database object,
    supply ``list`` and ``create`` actions.

    This must be subclass and mixin with a database mixin
    which supports database operation such as:
    ``db_query, db_insert`, `db_serialize``, and ``db_select``

    To check permissions, overide ``prepare`` method.
    """

    REPO = 'Resource'
    URL_PREFIX = '/api'
    TABLE = None

    @coroutine
    def get(self):  # list items
        t, q = self.db_prepare(self.TABLE)
        rows = yield self.db_select(q.fields('*'))
        rows = self.db_serialize(rows)
        self.write_json(length=len(rows), items=rows)

    @coroutine
    def post(self):
        self.set_status(201)
        ret = yield self.db_insert(self.TABLE, self.data)
        self.write_json(ret=ret)


class Item(ErrorMixin, JsonMixin, Request):
    """
    This similar to `Resource` class, supply get an item out of list and
    PATCH/DELETE actions.
    """
    REPO = 'Item'
    URL_PREFIX = '/api'
    TABLE = None

    @coroutine
    def get(self, row_id):
        t, q = self.db_prepare(self.TABLE, row_id=row_id)
        rows = yield self.db_select(q.fields('*'))
        self.write_json(item=rows[0])

    @coroutine
    def patch(self, row_id):
        if not self.data:
            raise HTTPError(400, 'No data to patch')
        ret = yield self.db_update(
            self.TABLE, row_id, self.data
        )
        self.write_json(status='ok', detail=ret)

    @coroutine
    def delete(self, row_id):
        ret = yield self.db_delete(self.TABLE, row_id)
        self.write_json(status='ok', detail=ret)


@on('init')
def register_resources_items(self):
    """
    Quicky register all possible routes to a `Resource` and/or an `Item`
    """
    request_repo = Registry._repo['Request']
    resources = Registry.known('Resource')
    items = Registry.known('Item')

    for resource in resources:
        if not resource.TABLE:
            continue
        if not resource.URL:
            resource.URL = r'^{prefix}/{res}/?$'.format(
                prefix=resource.URL_PREFIX,
                res=resource.TABLE
            )
        request_repo.append(resource)

    logger.debug('Items: %s', [r.TABLE for r in items])
    for item in items:
        if not resource.TABLE:
            continue
        if not item.URL:
            item.URL = r'^{prefix}/{res}/({id})/?$'.format(
                prefix=resource.URL_PREFIX,
                res=resource.TABLE,
                id=SHORT_UUID_RE)
        request_repo.append(item)


class PlainApi(ErrorMixin, JsonMixin, Request):
    REPO = 'Request'
    TABLE = None


class ValidationError(HTTPError):

    def __init__(self, errors, *args, **kwargs):
        self.status_code = 400
        self.log_message = None
        self.reason = 'Validation failed {}'.format(', '.join(tuple(errors.keys())))
        self.detail = errors

class ValidatorMixin:

    SCHEMA = None

    def validate(self):
        if not self.SCHEMA:
            raise ValueError("Cannot validate because schema isn't set")
        self.validator = Validator(self.SCHEMA)
        if not self.validator.validate(self.data):
            raise ValidationError(self.validator.errors)


class CreateMixin(ValidatorMixin):

    @coroutine
    def on_create(self, data):
        inserted_id = yield self.db_insert(self.TABLE, **data)
        return inserted_id

    @coroutine
    def post(self):
        self.validate()
        try:
            ret = yield self.on_create(self.validator.document)
        except self.DbIntegrityError as e:
            self.set_status(400)
            self.write_json({'reason': str(e)})
        except self.DbError as e:
            self.set_status(500)
            self.write_json({'reason': str(e)})
        else:
            self.set_status(201)
            self.write_json({
                'id': ret
            })

class UpdateMixin(ValidatorMixin):

    @coroutine
    def on_update(self, data, uid):
        changes = yield self.db_update(self.TABLE, uid, data)
        return changes

    @coroutine
    def put(self, uid):
        self.validate()
        try:
            changes = yield self.on_update(self.validator.document, uid)
        except self.DbError as e:
            self.set_status(500)
            self.write_json({'reason': str(e)})
        else:
            self.set_status(200)
            self.finish()
