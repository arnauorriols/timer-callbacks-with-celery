Callback Scheduling with Celery DEMO
==================================

Description
-----------

This piece of code is an example of how to implement a callback scheduling system
using the event loop of the Celery workers.

When the celery worker starts, it goes through a series of steps, until it's
fully loaded. This steps, called 'bootsteps', can be part of the 2 stages that
this loading process is composed by. In this stages, called "Blueprints", all
components are started, including the event loop (hub) and the timer.

As explained in [the Celery documentation](http://celery.readthedocs.org/en/latest/userguide/extending.html#timer-scheduling-events)
these blueprints can be used to hook all we want to these differents stages.
Then, We can use the timer in the Worker Blueprint to schedule callbacks to be
called after some time.

We may use the call_after() method of the timer, but there is one problem:
For every message received, Celery creates a sub-process to call the task.
In this escenario, we couldn't access the entry (the object representing the
callback in the timer) created in another process to cancel it if wanted to.
Therefore, the solution can be to use a multiprocessing.Queue (actually two)
to communicate between the tasks and the Timer.

Dependencies
------------
* Celery
* Requests (just for the demo callback)
* mock (for the tests)

Usage
-----
To see this demo in action, start the worker in the foreground:

```
celery -A celery_task worker -l info
```

Then, hit amqp with Celery or whichever tool you fancy. Just remember, if you
are using anything other than Celery, the message payload **must** be a dict
(by default JSON-encoded, remember to set the properties content_type and
content_encoding!) like this:

```python
{
    "task": "celery_task.foo",  # Name of the task that will consume the message
    "id": 123123,  # No idea what is this for, I put it randomly :)
    "args": ["foo"]  # Arguments to pass to the task.
}
```

If everything works as expected, you should see a countdown and finally your ip
printed in the Celery worker's log.

```
[tasks]
  . celery_task.foo

[2014-06-18 20:37:06,824: WARNING/MainProcess] Setting up the timer task
[...]
[2014-06-18 20:37:29,831: INFO/MainProcess] Received task: celery_task.foo[1]
[2014-06-18 20:37:29,836: INFO/MainProcess] Task celery_task.foo[1] succeeded in 0.00298441102495s: None
[2014-06-18 20:37:30,839: WARNING/MainProcess] demo callback_1403116649.83 still not called, remaining: -3.99460506439
[2014-06-18 20:37:31,843: WARNING/MainProcess] demo callback_1403116649.83 still not called, remaining: -2.99099707603
[2014-06-18 20:37:32,845: WARNING/MainProcess] demo callback_1403116649.83 still not called, remaining: -1.98825097084
[2014-06-18 20:37:33,849: WARNING/MainProcess] demo callback_1403116649.83 still not called, remaining: -0.984619140625
[2014-06-18 20:37:34,852: WARNING/MainProcess] Firing demo callback_1403116649.83
[2014-06-18 20:37:34,874: INFO/MainProcess] Starting new HTTP connection (1): httpbin.org
[2014-06-18 20:37:35,178: WARNING/MainProcess] *** TO BE SEEN IN CELERY LOG ***

Your IP is: 78.145.112.139

```

Tests
-----
To run the tests, as usual:

```
$ python tests.py
```

Just remember the mock dependency (how do you live without it?)
