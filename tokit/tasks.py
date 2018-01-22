import os
import logging
from inspect import iscoroutinefunction
from email.mime.text import MIMEText
from email.header import Header
import smtplib
from concurrent.futures import ThreadPoolExecutor
from threading import Thread

from tornado.queues import PriorityQueue, QueueEmpty
from tornado.gen import sleep, coroutine
from tornado.ioloop import IOLoop
from tornado.concurrent import run_on_executor
logger = logging.getLogger('pq.tasks')
from tokit import Event, on

# time to sleep wait for new job
SLEEP_INTERVAL = 0.3

# in-memory storage
simple_queue = PriorityQueue()


# reference https://hackernoon.com/controlling-python-async-creep-ec0a0f4b79ba

def simple_queue_put(name, *args, priority=0, **kwargs):
    """
    Schedule a task with given params

    Handlers of event with same name will be used when execute task

    Example::

        @on('task_xyz')
        def do_something(arg1):
            pass

        put('task_xyz', 'val1')
    """
    simple_queue.put((priority, {'name': name, 'args': args, 'kwargs': kwargs}))
    
async def execute_task(app, task):
    handlers = Event.get(task['name']).handlers
    for handler in handlers:
        if iscoroutinefunction(handler):
            yield handler(
                app,
                *task.get('args'),
                **task.get('kwargs')
            )
        else:
            yield app._thread_executor.submit(
                handler,
                app,
                *task.get('args'),
                **task.get('kwargs')
            )
    else:
        logger.warn('No handler for task: %s', task['name'])

@coroutine
def simple_queue_consumer(app):
    """
    Check for pending and excute tasks

    A task handler can be coroutine (run in event loop)
    or normal function (run in thread - can be blocking)
    """
    while True:
        try:
            priority, task = simple_queue.get_nowait()
            yield execute_task(app, task)
        except QueueEmpty:
            yield sleep(SLEEP_INTERVAL)
        else:
            simple_queue.task_done()


def register_simple_queue(app):
    IOLoop.current().spawn_callback(lambda: simple_queue_consumer(app))
    
try:
    # git@github.com:manhg/pq.git
    from pq.tasks import PQ, Queue
except:
    pass
else:
    from psycopg2.pool import ThreadedConnectionPool
    pq_manager = PQ(
        table='task_queues',
        queue_class=Queue
    )
    db_queue = pq_manager['default']

    def db_queue_work():
        logger.info('Queue worker started')
        db_queue.work()

    def db_queue_put(name, *args, **kwargs):
        db_queue.put({'name': name, 'args': args, 'kwargs': kwargs})

    def register_db_queue(app):
        env = app.config.env['postgres']
        pool = ThreadedConnectionPool(minconn=1, maxconn=env['size'], dsn=env['dsn'])
        pq_manager.pool = pool
        db_queue.pool = pool

        # Notice: process queue in another thread
        # be careful with non thread-safe operations
        worker_thread = Thread(target=db_queue_work)
        worker_thread.start()

        @on('stop')
        def unregister_db_queue():
            logger.info('Stop queue worker')
            worker_thread.join()
            if worker_thread.is_alive():
                worker_thread.set()


@on('send_email')
@coroutine
def send_email_consumer(app, receipt, body, subject=None):
    if not subject:
        # consider first line as subject
        subject, body = body.split("\n", 1)
    msg = MIMEText(body, 'plain', 'utf-8')
    config = app.config.env['smtp']
    msg['Subject'] = Header(subject, 'utf-8')
    msg['From'] = config['from']
    msg['To'] = receipt
    with smtplib.SMTP(config['host'], config.get('port')) as mailer:
        if config.getboolean('tls'):
            mailer.starttls()
        if config.get('user'):
            mailer.login(config.get('user'), config['password'])
        mailer.send_message(msg)
        mailer.quit()
    logger.debug("Sent email to %s", receipt)


class EmailMixin:

    def send_email(self, template, receipt, **kwargs):
        content = self.render_string(
            os.path.join(self.application.root_path, template), **kwargs
        ).decode()
        simple_queue_put('send_email', receipt, content)


@on('init')
def init_executor(app):
    max_thread_worker = app.config.env['app'].getint('max_thread_worker', 16)
    app._thread_executor = ThreadPoolExecutor(max_workers=max_thread_worker)


class ThreadPoolMixin:
    """ Mix this and wrap blocking function with ``run_on_executor`` """

    @property
    def executor(self):
        return self.application._thread_executor
