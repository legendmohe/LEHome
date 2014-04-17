#!/usr/bin/env python
# encoding: utf-8

from util.log import *


class stop_callback:
    def callback(self, stop = None):
        DEBUG("stop command:", stop)
        return True, "stop"
