# SPDX-License-Identifier: MIT
"""BLE operation queue without Kivy Clock."""

from __future__ import annotations

import threading
from functools import partial, wraps
from queue import Empty, Queue


def ble_task(method):
    @wraps(method)
    def wrapper(obj, *args, **kwargs):
        task = partial(method, obj, *args, **kwargs)
        obj.queue.enque(task)

    return wrapper


def ble_task_done(method):
    @wraps(method)
    def wrapper(obj, *args, **kwargs):
        obj.queue.done()
        return method(obj, *args, **kwargs)

    return wrapper


class BLEQueue:
    def __init__(self, timeout=0.0):
        self.lock = threading.Lock()
        self.ready = True
        self.queue = Queue()
        self.timeout = float(timeout or 0.0)
        self._timer = None

    def set_timeout(self, timeout):
        self.timeout = float(timeout or 0.0)

    def enque(self, task):
        if self.timeout == 0:
            self.execute_task(task)
            return
        self.queue.put_nowait(task)
        self.execute_next()

    def execute_next(self, ready=False):
        with self.lock:
            if ready:
                self.ready = True
            elif not self.ready:
                return
            try:
                task = self.queue.get_nowait()
            except Empty:
                return
            self.ready = False
        if task is not None:
            self.execute_task(task)

    def done(self, *args, **kwargs):
        timer = self._timer
        self._timer = None
        if timer is not None:
            try:
                timer.cancel()
            except Exception:
                pass
        self.execute_next(ready=True)

    def execute_task(self, task):
        if self.timeout > 0:
            timer = threading.Timer(self.timeout, self.done)
            timer.daemon = True
            self._timer = timer
            timer.start()
        task()
