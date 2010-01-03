#!/usr/bin/env python
# encoding: utf-8

from lib.command.LE_Command import *
from lib.speech.LE_Speech import *
from time import sleep
from pprint import pprint
import importlib
import logging as log
import sys
import traceback

from usr.LE_Res import LE_Res

class TracePrints(object):
      def __init__(self):    
          self.stdout = sys.stdout
      def write(self, s):
          self.stdout.write("Writing %r\n" % s)
          traceback.print_stack(file=self.stdout)

# sys.stdout = TracePrints()

class LE_Home:
    def __init__(self):
        self.__confidence_threshold = 0.6
        self.__context = {}
        self.__init_command()
        self.__init_recognizer()
        self.__init_speaker()

    def __init_command(self):
        print 'initlizing command...'

        settings = LE_Res.init("init.json")
        if settings:

            com_json = settings['command']
            self.__com = LE_Command(
                    trigger = com_json["trigger"],
                    action = com_json["action"],
                    target =  com_json["target"],
                    stop =  com_json["stop"],
                    finish =  com_json["finish"],
                    then =  com_json["then"],
                    DEBUG = False)
            
            cb_json = settings["callback"]
            for com_name in cb_json.keys():
                cbs = cb_json[com_name]
                for cb_token in cbs.keys():
                    try:
                        token = cbs[cb_token].encode("utf-8")
                        dpos = token.rindex('.')
                        module_name = token[:dpos]
                        class_name = token[dpos + 1:]
                        cb_module_name = "usr.callbacks.%s.%s" %(com_name, module_name)
                        cb_module = importlib.import_module(cb_module_name)
                        # pprint(dir(cb_module))
                        cb_object = getattr(cb_module, class_name)()
                        cb_object.__context = self.__context
                        
                        print "load callback: " + cb_module_name + " for command token:" + cb_token
                        self.__com.register_callback(
                                    com_name,
                                    cb_token,
                                    cb_object.callback)
                    except Exception, e:
                        log.exception("init commands faild.")

    def __init_recognizer(self):
        print 'initlizing recognizer...'
        
        self.__rec = LE_Speech2Text(self.__speech_callback)

    def __init_speaker(self):
        print "initlizing speaker..."

        self.__spk = LE_Text2Speech()

    def __speech_callback(self, result, confidence):
        print "result: " + result + " | " + str(confidence)
        if confidence > self.__confidence_threshold:
            self.__com.parse(result)

    def activate(self):
        print "=============================Activate==================================="
        self.__com.start()
        self.__rec.start_recognizing()
        self.__spk.start()
        self.__spk.speak(u"你好，我叫贝多芬。")

    def deactivate(self):
        self.__com.stop()
        self.__rec.stop_recognizing()
        self.__spk.stop()


if __name__ == '__main__':
    home = LE_Home()
    home.activate()
    sleep(1000)
    
