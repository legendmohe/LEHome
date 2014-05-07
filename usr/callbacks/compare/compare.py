#!/usr/bin/env python
# encoding: utf-8
from util.log import *
from lib.model import Callback


class compare_callback(Callback.Callback):
    def callback(self, aValue, bValue):
        DEBUG("compare callback invoke.")
        print "compare: ", aValue, bValue
        return aValue == bValue
