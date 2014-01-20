#!/usr/bin/env python
# encoding: utf-8

class open_light_callback:
    def callback(self, trigger, action, target, message, finish, pass_value = None):
        print "* trigger: %s action: %s, target: %s, message: %s >> %s" %(trigger, action, target, message, finish)
