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
