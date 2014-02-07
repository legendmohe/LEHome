#!/usr/bin/env python
# encoding: utf-8

class stop_callback:
    def callback(self, stop = None):
        print "stop command:", stop
        return True, "stop"
