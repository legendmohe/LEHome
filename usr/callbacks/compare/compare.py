#!/usr/bin/env python
# encoding: utf-8
from util.log import *
from lib.model import Callback


class compare_callback(Callback.Callback):
    def callback(self, aValue, bValue):
        DEBUG("compare callback invoke.")
        return aValue == bValue


class equal_callback(Callback.Callback):
    def callback(self, aValue, bValue):
        return aValue == bValue


class greater_callback(Callback.Callback):
    def callback(self, aValue, bValue):
        return aValue > bValue


class less_callback(Callback.Callback):
    def callback(self, aValue, bValue):
        return aValue < bValue


class not_equal_callback(Callback.Callback):
    def callback(self, aValue, bValue):
        return not (aValue == bValue)
