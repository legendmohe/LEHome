#!/usr/bin/env python
# encoding: utf-8

from lib.command.LE_Command import *
from lib.tts.LE_Speech_Recognizer import *
from time import sleep
import json

import sys;
sys.path.append("./usr/callbacks/")

class LE_Home:
    def __init__(self):
        self.__confidence_threshold = 0.6
        self.__context = {}
        self.__init_command()
        self.__init_recognizer()

    def __init_command(self):
        print 'initlizing command...'

        with open("usr/init.json") as init_file:
            init_json = json.load(init_file)
            if not init_json:
                print "error: invaild init.json."
                return

            com_json = init_json['command']
            self.__com = LE_Command(
                    trigger = com_json["trigger"],
                    action = com_json["action"],
                    target =  com_json["target"],
                    stop =  com_json["stop"],
                    finish =  com_json["finish"],
                    then =  com_json["then"],
                    DEBUG = False)
            
            cb_json = init_json["callback"]
            for cb_name in cb_json.keys():
                try:
                    cb_module_name = cb_json[cb_name].encode("utf-8")
                    cb_module = __import__(cb_module_name)
                    cb_object = getattr(cb_module, cb_module_name)()
                    print "load callback: " + cb_module_name + " for command:" + cb_name
                    self.__com.register_callback(
                                cb_name
                                , cb_object.callback)
                except Exception as e:
                    print e

    def __init_recognizer(self):
        print 'initlizing recognizer..'
        
        self.__rec = LE_Speech_Recognizer(self.__speech_callback)

    def __speech_callback(self, result, confidence):
        print "result: " + result + " | " + str(confidence)
        if confidence > self.__confidence_threshold:
            self.__com.parse(result)

    def activate(self):

        print "=============================Activate==================================="

        self.__com.start()
        self.__rec.start_recognizing()

    def deactivate(self):
        self.__com.stop()
        self.__rec.stop_recognizing()


if __name__ == '__main__':
    home = LE_Home()
    home.activate()
    sleep(100)
    
