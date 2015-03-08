#!/usr/bin/env python
# encoding: utf-8
# Copyright 2014 Xinyu, He <legendmohe@foxmail.com>
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#   http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import threading


class StoppableThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self, target, args=None):
        super(StoppableThread, self).__init__(target=target, args=args)
        self._stop = threading.Event()
        self.suspend_event = None
        self.thread_idx = -1

    def waitUtil(self, sec):
        self._stop.wait(sec)

    def stop(self):
        if not self.suspend_event is None:
            self.suspend_event.set()
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
