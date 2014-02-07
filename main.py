#!/usr/bin/env python
# encoding: utf-8

from lib.command.LE_Command import LE_Command
from lib.speech.LE_Speech import LE_Speech2Text, LE_Text2Speech
from time import sleep
import importlib
import logging as log
import sys
import traceback
from util.LE_Res import LE_Res
from lib.sound import LE_Sound


class TracePrints(object):
      def __init__(self):    
          self.stdout = sys.stdout
      def write(self, s):
          self.stdout.write("Writing %r\n" % s)
          traceback.print_stack(file=self.stdout)

# sys.stdout = TracePrints()


class LE_Home:
    def __init__(self):
        self._confidence_threshold = 0.5
        self._context = {}
        self._init_speaker()
        self._init_recognizer()
        self._init_command()

    def _init_command(self):
        print 'initlizing command...'

        settings = LE_Res.init("init.json")
        if settings:

            com_json = settings['command']
            self._com = LE_Command({
                        "whiles":com_json["while"],
                        "ifs":com_json["if"],
                        "thens":com_json["then"],
                        "elses":com_json["else"],
                        "delay":com_json["delay"],
                        "trigger":com_json["trigger"],
                        "action":com_json["action"],
                        "target":com_json["target"],
                        "stop":com_json["stop"],
                        "finish":com_json["finish"],
                        "nexts":com_json["next"],
                        })
            self._com.setDEBUG(False)
            
            cb_json = settings["callback"]
            for com_name in cb_json.keys():
                cbs = cb_json[com_name]
                for cb_token in cbs.keys():
                    try:
                        token = cbs[cb_token].encode("utf-8")
                        if token == "" or token is None:
                            print "token ", token, " no callbacks."
                            continue
                        dpos = token.rindex('.')
                        module_name = token[:dpos]
                        class_name = token[dpos + 1:]
                        cb_module_name = "usr.callbacks.%s.%s" %(com_name, module_name)
                        cb_module = importlib.import_module(cb_module_name)
                        # pprint(dir(cb_module))
                        cb_object = getattr(cb_module, class_name)()
                        cb_object._context = self._context
                        cb_object._speaker = self._spk
                        cb_object._rec = self._rec
                        
                        print "load callback: " + cb_module_name + " for command token:" + cb_token
                        self._com.register_callback(
                                    com_name,
                                    cb_token,
                                    cb_object.callback)
                    except Exception, e:
                        log.exception("init commands faild.")

    def _init_recognizer(self):
        print 'initlizing recognize...'
        # LE_Speech2Text.collect_noise()
        self._rec = LE_Speech2Text(self._speech_callback)

    def _init_speaker(self):
        print "initlizing speaker..."

        self._spk = LE_Text2Speech()

    def _speech_callback(self, result, confidence):
        print "result: " + result + " | " + str(confidence)
        if confidence > self._confidence_threshold:
            self._com.parse(result)

    def activate(self):
        print "==========================Activate============================"
        LE_Sound.playmp3(
                        LE_Res.get_res_path("sound/com_begin")
                        )
        self._spk.start()
        self._com.start()
        self._rec.start_recognizing()

    def deactivate(self):
        self._spk.stop()
        self._com.stop()
        self._rec.stop_recognizing()


if __name__ == '__main__':
    home = LE_Home()
    home.activate()
    sleep(1000)
    
