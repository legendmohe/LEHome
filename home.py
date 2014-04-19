#!/usr/bin/env python
# encoding: utf-8


import sys
import importlib
import traceback
import argparse
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
    def __init__(self, cmd_source, audio_server):
        self._context = {}
        self._init_speaker()
        self._init_command()
        self._init_cmd_source(cmd_source)
        self._init_audio_server(audio_server)
        self._resume = False

    def _init_command(self):
        INFO('initlizing command...')

        settings = Res.init("init.json")
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
                        cb_module_name = "usr.callbacks.%s.%s" %(com_name, module_name)
                        cb_module = importlib.import_module(cb_module_name)
                        cb_object = getattr(cb_module, class_name)()
                        cb_object._context = self._context
                        cb_object._speaker = self._spk
                        cb_object._home = self
                                   
                        INFO("load callback: " + cb_module_name + " for command token:" + cb_token)
                        self._com.register_callback(
                                    com_name,
                                    cb_token,
                                    cb_object.internal_callback)
                    except Exception, e:
                        ERROR("init commands faild.")
                        ERROR(e)

    def _init_speaker(self):
        INFO("initlizing speaker...")
        self._spk = Text2Speech()

    def _init_audio_server(self, audio_server):
        Sound.AUDIO_SERVER_ADDRESS = audio_server

    def _init_cmd_source(self, cmd_source):
        if not cmd_source is None:
            INFO("connect to s2t server: %s " % (cmd_source))
            context = zmq.Context()
            _sock = context.socket(zmq.SUB)
            _sock.connect(cmd_source)
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
    parser = argparse.ArgumentParser(
            description='home.py -s tcp://address:port -a http://address:port')
    parser.add_argument('-s',
                        action="store",
                        dest="cmd_source",
                        default="tcp://localhost:8000",
                        help="s2t server address and port")
    parser.add_argument('-a',
                        action="store",
                        dest="audio_server",
                        default="http://localhost:8001",
                        help="audio server address and port")
    args = parser.parse_args()

    cmd_source = args.cmd_source
    audio_server = args.audio_server
    INFO("connect to s2t server: %s " % (cmd_source))
    INFO("connect to audio server: %s " % (audio_server))

    home = Home(cmd_source, audio_server)
    home.activate()
