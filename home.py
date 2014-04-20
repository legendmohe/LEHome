#!/usr/bin/env python
# encoding: utf-8


import sys
import importlib
import traceback
import zmq
from lib.command.Command import Command
from lib.speech.Speech import Text2Speech
from util.Res import Res
from lib.sound import Sound
from util.log import *


class TracePrints(object):
      def __init__(self):    
          self.stdout = sys.stdout
      def write(self, s):
          self.stdout.write("Writing %r\n" % s)
          traceback.print_stack(file=self.stdout)

# sys.stdout = TracePrints()


class Home:
    def __init__(self):
        self._context = {}
        self._init_res = Res.init("init.json")
        self._init_speaker()
        self._init_command()
        self._init_cmd_source()
        self._init_audio_server()
        self._resume = False

    def _init_command(self):
        INFO('initlizing command...')
        
        settings = self._init_res
        if settings:
            com_json = settings['command']
            self._com = Command({
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

            import traceback
            
            cb_json = settings["callback"]
            for com_name in cb_json.keys():
                cbs = cb_json[com_name]
                for cb_token in cbs.keys():
                    try:
                        token = cbs[cb_token].encode("utf-8")
                        if token == "" or token is None:
                            WARN("token ", token, " no callbacks.")
                            continue
                        dpos = token.rindex('.')
                        module_name = token[:dpos]
                        class_name = token[dpos + 1:]
                        cb_module_name = "usr.callbacks.%s.%s" % (com_name, module_name)
                        cb_module = importlib.import_module(cb_module_name)
                        cb_object = getattr(cb_module, class_name)()
                        cb_object._context = self._context
                        cb_object._speaker = self._spk
                        cb_object._home = self
                                   
                        DEBUG("load callback: " + cb_module_name + " for command token:" + cb_token)
                        self._com.register_callback(
                                    com_name,
                                    cb_token,
                                    cb_object.internal_callback)
                    except Exception, e:
                        ERROR("init commands faild.")
                        print traceback.format_exc()

    def _init_speaker(self):
        INFO("initlizing speaker...")
        self._spk = Text2Speech()

    def _init_audio_server(self):
        Sound.AUDIO_SERVER_ADDRESS = self._init_res["connection"]["audio_source"]
        INFO("connect to audio server: %s " % (Sound.AUDIO_SERVER_ADDRESS))

    def _init_cmd_source(self):
        context = zmq.Context()
        _sock = context.socket(zmq.SUB)
        sources = self._init_res["connection"]["cmd_source"]
        for source in sources:
            try:
                _sock.connect(source)
                INFO("connect to command source: %s " % (source))
            except Exception, e:
                ERROR("connection faild: %s" % (source, ))
                ERROR(e)
        _sock.setsockopt(zmq.SUBSCRIBE, '')
        self._sock = _sock

    def parse_cmd(self, cmd):
        if not self._resume:
            INFO("command: " + cmd)
            self._com.parse(cmd)

    def activate(self):
        INFO("home activate!")
        Sound.play(Res.get_res_path("sound/com_begin"))
        self._spk.start()
        self._com.start()

        while True:
            INFO("waiting for command...")
            cmd = self._sock.recv_string()
            home.parse_cmd(cmd)

    def deactivate(self):
        self._spk.stop()
        self._com.stop()

    def setResume(self, resume):
        self._resume = resume


if __name__ == '__main__':
    home = Home()
    home.activate()
