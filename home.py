#!/usr/bin/env python
# encoding: utf-8


import sys
import importlib
import traceback
import threading
import time
import json
import zmq
from lib.command.Command import Command
from lib.speech.Speech import Text2Speech
from lib.helper.SwitchHelper import SwitchHelper
from lib.helper.SensorHelper import SensorHelper
from lib.helper.MessageHelper import MessageHelper
from util.Res import Res
from lib.sound import Sound
from util.log import *
from util.thread import TimerThread


class TracePrints(object):
      def __init__(self):    
          self.stdout = sys.stdout
      def write(self, s):
          self.stdout.write("Writing %r\n" % s)
          traceback.print_stack(file=self.stdout)

# sys.stdout = TracePrints()


class Home:
    def __init__(self):

        self._global_context = {}
        self._init_res = Res.init("init.json")
        self._init_subscribable()
        self._init_audio_server()
        self._init_helper()
        self._init_speaker()
        self._init_command()

        self._resume = False
        self._cmd.init_tasklist()  # load unfinished task

        self.publish_msg("init", u"服务器启动")

    def _init_command(self):
        INFO('initlizing command...')
        
        def info_sender(info_type, info):
            pass
            # if info_type == 'begin':
            #     msg = u'执行命令:'
            # elif info_type == 'end':
            #     msg = u'执行完毕:'
            #     info = msg + info
            # self.publish_msg(info, info)

        settings = self._init_res
        if settings:
            com_json = settings['command']
            self._cmd = Command({
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
                        "logical":com_json["logical"],
                        "compare":com_json["compare"],
                        }, info_sender=info_sender)
            self._cmd.setDEBUG(False)
            self._cmd.cmd_begin_callback = self._cmd_begin_callback
            self._cmd.cmd_end_callback = self._cmd_end_callback

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
                        cb_object._global_context = self._global_context
                        cb_object._class_context = {}
                        cb_object._speaker = self._spk
                        cb_object._home = self
                                   
                        DEBUG("load callback: " + cb_module_name + " for command token:" + cb_token)
                        self._cmd.register_callback(
                                    com_name,
                                    cb_token,
                                    cb_object)
                    except Exception, e:
                        ERROR("init commands faild.")
                        print traceback.format_exc()

    def _init_speaker(self):
        INFO("initlizing speaker...")
        self._spk = Text2Speech()

    def _init_audio_server(self):
        Sound.AUDIO_SERVER_ADDRESS = self._init_res["connection"]["audio_server"]
        INFO("connect to audio server: %s " % (Sound.AUDIO_SERVER_ADDRESS))

    def _init_subscribable(self):
        context = zmq.Context()
        _sub_sock = context.socket(zmq.SUB)
        subscribables = self._init_res["connection"]["subscribable"]
        for subscribable in subscribables:
            try:
                _sub_sock.connect(subscribable)
                INFO("connect to subscribable: %s " % (subscribable))
            except Exception, e:
                ERROR("connection faild: %s" % (subscribable, ))
                ERROR(e)
        _sub_sock.setsockopt(zmq.SUBSCRIBE, '')
        self._sub_sock = _sub_sock
        #  for receiving init string too fast
        time.sleep(0.5)

    def _init_helper(self):
        publisher_ip = self._init_res["connection"]["publisher"]
        msg_cmd_bind = self._init_res["connection"]["msg_cmd_bind"]
        INFO("init message publisher: %s, cmd bind: %s" %
                                            (publisher_ip, msg_cmd_bind))
        self._msg_sender = MessageHelper(publisher_ip, msg_cmd_bind)

        switch_server_ip = self._init_res["connection"]["switch_server"]
        INFO("init switch server: " + switch_server_ip)
        self._switch = SwitchHelper()

        sensor_server_ip = self._init_res["connection"]["sensor_server"]
        INFO("init sensor server: " + sensor_server_ip)
        self._sensor = SensorHelper()

    def _cmd_begin_callback(self, command):
        INFO("command begin: %s" % (command))
        # self.publish_msg(command, u"执行: " + command)

    def _cmd_end_callback(self, command):
        INFO("command end: %s" % (command))
        # self.publish_msg(command, "end: " + command)

    def publish_msg(self, sub_id, msg, cmd_type="normal"):
        self._msg_sender.publish_msg(sub_id, msg, cmd_type)

    def parse_cmd(self, cmd):
        if not self._resume:
            INFO("command: " + cmd)
            self._cmd.parse(cmd)

    def activate(self):
        INFO("home activate!")
        Sound.play(Res.get_res_path("sound/com_begin"))
        self._spk.start()
        self._cmd.start()

        while True:
            INFO("waiting for command...")
            cmd = self._sub_sock.recv_string()
            home.parse_cmd(cmd)

    def deactivate(self):
        self._spk.stop()
        self._cmd.stop()

    def setResume(self, resume):
        self._resume = resume


if __name__ == '__main__':
    home = Home()
    home.activate()
