#!/usr/bin/env python
# encoding: utf-8

import threading


class StoppableThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self, target, args=None):
        super(StoppableThread, self).__init__(target=target, args=args)
        self._stop = threading.Event()

    def waitUtil(self, sec):
        self._stop.wait(sec)

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()


class TimerThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self, interval, target, args={}):
        super(TimerThread, self).__init__()
        self.interval = interval
        self.target = target
        self.args = args
        self._stop = threading.Event()
        self.setDaemon(True)  # don't forget to set daemon

    def run(self):
        while not self._stop.wait(self.interval):
            self.target(**self.args)

    def stop(self):
        self._stop.set()

    def set_stopped(self):
        return self._stop.isSet()
