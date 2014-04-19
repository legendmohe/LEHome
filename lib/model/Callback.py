#!/usr/bin/env python
# encoding: utf-8


import inspect
from util.log import *


class Callback:
    def __init__(self):
        if not callable(getattr(self, "callback")):
            ERROR("callback method not found.")
            return
        self.callback_param_names = inspect.getargspec(self.callback)[0]
        if "self" in self.callback_param_names:
            self.callback_param_names.remove("self")

    def internal_callback(self, **kwargs):
        call_dict = {}
        for key in self.callback_param_names:
            if key in kwargs:
                call_dict[key] = kwargs[key]
            else:
                call_dict[key] = None
        DEBUG("callback: %s" % (kwargs, ))
        self.callback(**call_dict)
