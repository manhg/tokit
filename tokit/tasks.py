import os
from concurrent.futures import ThreadPoolExecutor

from tornado.queues import PriorityQueue, QueueEmpty
from tornado.gen import sleep, coroutine
from tokit import Event, on, logger
from inspect import iscoroutinefunction
from email.mime.text import MIMEText
import smtplib
from email.header import Header
from tornado.gen import coroutine
from tornado.concurrent import run_on_executor

tasks_queue = PriorityQueue()

def put(name, *args, priority=0, **kwargs):
    """
    Schedule a task with given params

    Handlers of event with same name will be used when execute task

    Example::

        @on('task_xyz')
        def do_something(arg1):
            pass

        put('task_xyz', 'val1')
    """
    tasks_queue.put((priority, {'name': name, 'args': args, 'kwargs': kwargs}))


@coroutine
def tasks_consumer(app):
    """
    Check for pending and excute tasks

    A task handler can be coroutine (run in event loop)
    or normal function (run in thread - can be blocking)
    """
    while True:
        # another way: use Postgres notfiy / listen
        # http://initd.org/psycopg/docs/advanced.html#asynchronous-notifications
        yield sleep(0.3)
        try:
            priority, task = tasks_queue.get_nowait()
            handlers = Event.get(task['name']).handlers
            handler = None
            for handler in handlers:
                if iscoroutinefunction(handler):
                    yield handler(
                        app,
                        *task.get('args'),
                        **task.get('kwargs')
                    )
                else:
                    with ThreadPoolExecutor() as executor:
                        yield executor.submit(
                            handler,
                            app,
                            *task.get('args'),
                            **task.get('kwargs')
                        )
            if not handler:
                logger.warn('No handler for task: %s', task['name'])
        except QueueEmpty:
            pass
        else:
            tasks_queue.task_done()


def register_task_runner(app):
    from tornado.ioloop import IOLoop
    IOLoop.current().spawn_callback(lambda: tasks_consumer(app))

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
        put('send_email', receipt, content)


@on('init')
def init_executor(app):
    max_thread_worker = app.config.env['app'].getint('max_thread_worker', 16)
    app._thread_executor = ThreadPoolExecutor(max_workers=max_thread_worker)


class ThreadPoolMixin:
    """ Mix this and wrap blocking function with ``run_on_executor`` """

    @property
    def executor(self):
        return self.application._thread_executor
