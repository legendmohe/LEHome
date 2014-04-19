#!/usr/bin/env python
# encoding: utf-8


from lib.model import Callback


class next_callback(Callback.Callback):
    def callback(self, action = None, target = None,
            msg = None, state = None, 
            pre_value = None, pass_value = None):
        DEBUG("* next callback: action: %s, target: %s, message: %s state: %s pre_value: %s pass_value %s" %(action, target, msg, state, pre_value, pass_value))
        return True, "pass"
