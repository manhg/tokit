from concurrent.futures import ThreadPoolExecutor

from tornado.queues import PriorityQueue, QueueEmpty
from tornado.gen import sleep, coroutine
from tokit import Event, on, logger
from inspect import iscoroutinefunction
from email.mime.text import MIMEText
import smtplib
from email.header import Header
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
async def send_email_consumer(app, receipt, body, subject=None):
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
        mailer.login(config['user'], config['password'])
        mailer.send_message(msg)
        mailer.quit()
    logger.debug("Sent email to %s", receipt)


class EmailMixin:

    def send_email(self, template, receipt, **kwargs):
        content = self.render_string(
            template, **kwargs
        ).decode()
        put('send_email', receipt, content)


class ThreadPoolMixin:
    """ Mix this and wrap blocking function with `run_on_executor` """

    _executor = None

    @property
    def executor(self):
        if not self._executor:
            max_thread_worker = self.application.config.env['app'].get('max_thread_worker', 16)
            self._executor = ThreadPoolExecutor(max_workers=max_thread_worker)
        return self._executor
