#!/usr/bin/env python
# encoding: utf-8

class stop_callback:
    def callback(self, action = None, target = None,
            msg = None, stop = None, 
            pre_value = None):
        print "* stop callback: action: %s, target: %s, message: %s stop: %s pre_value: %s" %(action, target, msg, stop, pre_value)
        return True, "pass"
