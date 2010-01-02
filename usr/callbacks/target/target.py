#!/usr/bin/env python
# encoding: utf-8

class target_callback:
    def callback(self, target = None,
            msg = None, 
            pre_value = None):
        print "* target callback: %s, message: %s pre_value: %s" %(target, msg, pre_value)
        return True, "pass"
