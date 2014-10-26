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



import inspect
from util.log import *


class Callback(object):
    def __init__(self):
        if not callable(getattr(self, "callback", None)):
            ERROR("callback method not found.")
            return
        self.callback_param_names = inspect.getargspec(self.callback)[0]
        DEBUG(self.callback_param_names)
        if "self" in self.callback_param_names:
            self.callback_param_names.remove("self")

        if callable(getattr(self, "canceled", None)):
            self.canceled_param_names = inspect.getargspec(
                                                            self.canceled
                                                            )[0]
            DEBUG(self.canceled_param_names)
            if "self" in self.canceled_param_names:
                self.canceled_param_names.remove("self")

    def internal_callback(self, **kwargs):
        call_dict = {}
        for key in self.callback_param_names:
            if key in kwargs:
                call_dict[key] = kwargs[key]
            else:
                call_dict[key] = None
        # DEBUG("callback: %s" % (kwargs, ))
        return self.callback(**call_dict)

    def internal_canceled(self, **kwargs):
        if not callable(getattr(self, "canceled", None)):
            return
        call_dict = {}
        for key in self.canceled_param_names:
            if key in kwargs:
                call_dict[key] = kwargs[key]
            else:
                call_dict[key] = None
        # DEBUG("canceled: %s" % (kwargs, ))
        return self.canceled(**call_dict)

    def redirect(self, c_type, c_name, **kwargs):
        if c_type is None or c_name is None:
            ERROR("invaild redirect params.")
            return
        else:
            cbs = self._home._cmd._registered_callbacks
            if not cbs is None and c_type in cbs and c_name in cbs[c_type]:
                return cbs[c_type][c_name].internal_callback(kwargs)
            else:
                ERROR("callback type or name is not exist.")
                return
