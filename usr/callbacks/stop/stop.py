#!/usr/bin/env python
# encoding: utf-8

from util.log import *
from lib.model import Callback


class stop_callback(Callback.Callback):
    def callback(self, stop = None):
        DEBUG("stop command:", stop)
        return True, "stop"
