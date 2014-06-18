#!/usr/bin/env python

import unittest
from multiprocessing import Queue
import time

import mock

from celery_task import WorkerBootstep


class CallbackMock(object):
    called = False
    wrong_called = False

    def __init__(self, wrong=False):
        if not wrong:
            CallbackMock.called = False
            CallbackMock.wrong_called = False
        self.flag_wrong = wrong

    def __call__(self):
        if not self.flag_wrong:
            CallbackMock.called = True
        else:
            CallbackMock.wrong_called = True


class TestWorkerBootStep(unittest.TestCase):

    def setUp(self):
        self.celery_worker = mock.Mock()
        self.worker_bootstep = WorkerBootstep(self.celery_worker)

    def test_start(self):
        self.worker_bootstep.start(self.celery_worker)
        self.celery_worker.timer.call_repeatedly.assert_called_once_with(
            WorkerBootstep.GRANULARITY,
            self.worker_bootstep.process_timers,
            args=(WorkerBootstep.QUEUE_ADD, WorkerBootstep.QUEUE_REMOVE)
        )

    def test_consume_queues(self):
        queue_add = Queue()
        queue_remove = Queue()
        now = time.time()
        callback_add = CallbackMock()
        callback_remove = lambda: 'not'
        self.worker_bootstep.callbacks = {
            'to_remove': {
                'callback': callback_remove,
                'ts_fire': now + 3
            }
        }
        to_add = ('to_add', callback_add, now + 3)
        to_remove = 'to_remove'
        queue_add.put(to_add)
        queue_remove.put(to_remove)
        self.worker_bootstep._consume_queues(queue_add, queue_remove)
        self.assertIn('to_add', self.worker_bootstep.callbacks)
        self.assertIsInstance(
            self.worker_bootstep.callbacks['to_add']['callback'],
            type(callback_add)
        )
        self.assertEqual(self.worker_bootstep.callbacks['to_add']['ts_fire'],
                         now + 3)

    @mock.patch('celery_task.time', new=mock.Mock(time=lambda: 5))
    def test_fire_timers(self):
        fired_call = mock.Mock()
        not_fired_call = mock.Mock()
        self.worker_bootstep.callbacks = {
            'fired': {
                'callback': fired_call,
                'ts_fire': 2,
            },
            'not_fired': {
                'callback': not_fired_call,
                'ts_fire': 6,
            }
        }
        self.worker_bootstep._fire_timers()
        self.assertIn('not_fired', self.worker_bootstep.callbacks)
        self.assertNotIn('fired', self.worker_bootstep.callbacks)
        self.assertTrue(fired_call.called)

    def test_process_timers(self):
        queue_add = Queue()
        queue_remove = Queue()
        now = time.time()
        callback_add = CallbackMock()
        callback_remove = CallbackMock(wrong=True)
        self.worker_bootstep.callbacks = {
            'to_remove': {
                'callback': callback_remove,
                'ts_fire': now + 0.01
            }
        }
        to_add = ('to_add', callback_add, now + 0.01)
        to_remove = 'to_remove'
        WorkerBootstep.QUEUE_ADD = queue_add
        WorkerBootstep.QUEUE_REMOVE = queue_remove
        queue_add.put(to_add)
        queue_remove.put(to_remove)
        self.worker_bootstep.process_timers(self.worker_bootstep.QUEUE_ADD,
                                            self.worker_bootstep.QUEUE_REMOVE)
        self.assertFalse(callback_add.called)
        time.sleep(0.1)
        self.worker_bootstep.process_timers(self.worker_bootstep.QUEUE_ADD,
                                            self.worker_bootstep.QUEUE_REMOVE)
        self.assertTrue(callback_add.called)
        self.assertFalse(callback_remove.wrong_called)


if __name__ == '__main__':
    unittest.main(verbosity=2)
