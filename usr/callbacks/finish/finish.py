#!/usr/bin/env python
# encoding: utf-8

from util.log import *   
from lib.model import Callback


class finish_callback(Callback.Callback):
    def callback(self, action = None, target = None,
            msg = None, finish = None, 
            pre_value = None):
        DEBUG("* finish callback: action: %s, target: %s, message: %s finish: %s pre_value: %s" %(action, target, msg, finish, pre_value))
        return True, pre_value
