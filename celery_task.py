from multiprocessing import Queue
import threading
from Queue import Empty
import time
import json

import requests
from celery import Celery, bootsteps


queue_add = Queue()
queue_remove = Queue()


class WorkerBootstep(bootsteps.StartStopStep):
    QUEUE_ADD = queue_add
    QUEUE_REMOVE = queue_remove
    GRANULARITY = 1

    def __init__(self, worker, **kwargs):
        print "Setting up Worker Bootstep"
        self.callbacks = {}

    def start(self, worker):
        """ Called by Celery when Bootstep is processed """
        print "Setting up the timer task"
        worker.timer.call_repeatedly(self.GRANULARITY, self.process_timers,
                                     args=(self.QUEUE_ADD, self.QUEUE_REMOVE))

    def process_timers(self, _queue_add, _queue_remove):
        """ Method fired repeatedly by the Celery Timer """
        self._consume_queues(_queue_add, _queue_remove)
        self._fire_timers()

    def _consume_queues(self, _queue_add, _queue_remove):
        """
        Extract all callbacks in the queues and add/remove them
        from the callbacks dict as appropiate.

        In the queue to add, expected payload is a tuple like so:
            (key_id, callback, ts_to_be_fired)

        In the queue to remove, only the key is expected

        """
        while True:
            try:
                key, callback, ts_fire = _queue_add.get(block=False)
            except Empty:
                break
            else:
                self.callbacks[key] = {'callback': callback,
                                       'ts_fire': ts_fire}

        while True:
            try:
                key = _queue_remove.get(block=False)
            except Empty:
                break
            else:
                try:
                    del self.callbacks[key]
                except KeyError:
                    # Proper logging warning. May happen if fired before being
                    # removed
                    pass

    def _fire_timers(self):
        """ If Any of the callback's timestamps is greater than now,
        fire the callback.

        Callbacks are fired on their own Thread. Also remove the callback
        from the callbacks dict.

        """
        _defered_delete = []
        for key, callback in self.callbacks.iteritems():
            if callback['ts_fire'] <= time.time():
                _defered_delete.append(key)
                threaded_callback = threading.Thread(
                    target=callback['callback']
                )
                print "Firing {0}".format(key)
                threaded_callback.start()
            else:
                print "{0} still not called, remaining: {1}".format(
                    key, time.time() - callback['ts_fire']
                )
        for key in _defered_delete:
            del self.callbacks[key]


def scream():
    """ Demo callback. requests httpbin.org/ip and prints your ip.

    The print result can be seen in the Celery worker's log.

    requires requests module.

    """
    res = requests.get('http://httpbin.org/ip')
    ip = json.loads(res.text)['origin']
    print """*** TO BE SEEN IN CELERY LOG ***

Your IP is: {0}

    """.format(ip)


app = Celery("tasks")
app.steps['worker'].add(WorkerBootstep)


@app.task
def foo(*args):
    """ Demo task of Celery. When receiving a new message, sets a new
    callback to be fired after 5 seconds.

    If publishing messages from outside Celery, remember that the payload
    required by Celery is a JSON object with these keys:
        {
            "task": "celery_task.foo",  # Name of the celery task
            "id": 123123,  # No idea of its utility, can be random for now
            "args": ["foo"]  # List with the arguments for the tas
        }

    """
    countdown = 5
    ts_fire = time.time() + countdown
    queue_add.put(('demo callback_{0}'.format(time.time()), scream, ts_fire))
