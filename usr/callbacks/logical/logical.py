#!/usr/bin/env python
# encoding: utf-8
from util.log import *
from lib.model import Callback


class logical_callback(Callback.Callback):
    def callback(self, aValue, bValue):
        DEBUG("logical callback invoke.")
        return aValue and bValue


class and_callback(Callback.Callback):
    def callback(self, aValue, bValue):
        # import pdb
        # pdb.set_trace()
        return aValue and bValue


class or_callback(Callback.Callback):
    def callback(self, aValue, bValue):
        return aValue or bValue
