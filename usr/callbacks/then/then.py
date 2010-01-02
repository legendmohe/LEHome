#!/usr/bin/env python
# encoding: utf-8

class then_callback:
    def callback(self, action = None, target = None,
            msg = None, state = None, 
            pre_value = None, pass_value = None):
        print "* then callback: action: %s, target: %s, message: %s state: %s pre_value: %s pass_value %s" %(action, target, msg, state, pre_value, pass_value)
        return True, "pass"
