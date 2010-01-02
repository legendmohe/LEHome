#!/usr/bin/env python
# encoding: utf-8

class action_callback:
    def callback(self, action = None, target = None,
            msg = None, 
            pre_value = None):
        print "* action callback: %s, target: %s, message: %s pre_value: %s" %(action, target, msg, pre_value)
        return True, "pass"
