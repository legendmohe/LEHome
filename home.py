#!/usr/bin/env python
# encoding: utf-8

# Copyright 2014 Xinyu, He <legendmohe@foxmail.com>
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#   http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import sys
import importlib
import traceback
import signal
import time

import tornado.ioloop
import tornado.web

import redis

import config
from lib.command.runtime import Rumtime
from lib.speech.Speech import Text2Speech
from lib.helper.SwitchHelper import SwitchHelper
from lib.helper.RilHelper import RilHelper
from lib.helper.SensorHelper import SensorHelper
from lib.helper.MessageHelper import MessageHelper
from lib.helper.TagHelper import TagHelper
from lib.helper.PingHelper import PingHelper
from lib.helper.GeoFencingHelper import GeoFencingHelper
from util.Res import Res
from lib.sound import Sound
from util.log import *


# class TracePrints(object):
#       def __init__(self):    
#           self.stdout = sys.stdout
#       def write(self, s):
#           self.stdout.write("Writing %r\n" % s)
#           traceback.print_stack(file=self.stdout)

# sys.stdout = TracePrints()


class Home:
    def __init__(self):

        INFO(u"==========服务器启动==========")
        INFO(u"DEBUG_ENABLE %s" % config.DEBUG_ENABLE)

        self._global_context = {}
        self._init_res = Res.init("init.json")
        self._init_storage()
        self._init_cmd_socket()
        self._init_audio_server()
        self._init_helper()
        self._init_speaker()
        self._init_command()

        self._resume = False
        self.runtime.init_tasklist()  # load unfinished task

        self.publish_msg("init", u"==========服务器启动==========")

    def _init_command(self):
        INFO('initlizing command...')
        
        settings = self._init_res
        if settings:
            com_json = settings['command']
            self.runtime = Rumtime({
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
                        })
            self.runtime.setDEBUG(False)
            self.runtime.cmd_begin_callback = self._cmd_begin_callback
            self.runtime.cmd_end_callback = self._cmd_end_callback

            module_cache = {}
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
                        cb_object = module_cache.get("%s.%s" % \
                                            (cb_module_name, class_name)
                                        )
                        if cb_object is None:
                            cb_module = importlib.import_module(cb_module_name)
                            cb_object = getattr(cb_module, class_name)()
                        cb_object.initialize(
                            _global_context = self._global_context,
                            _class_context  = {},
                            _speaker        = self._spk,
                            _home           = self,
                        )
                                   
                        DEBUG("load callback: " + cb_module_name + " for command token:" + cb_token)
                        self.runtime.register_callback(
                                    com_name,
                                    cb_token,
                                    cb_object)
                    except Exception, e:
                        ERROR("init commands faild.")
                        ERROR(traceback.format_exc())

    def _init_storage(self):
        host = self._init_res["storage"]["host"]
        port = self._init_res["storage"]["port"]
        INFO("initlizing storage:%s:%s" % (host, port))
        self._storage = redis.Redis(host=host, port=port)
        if self._storage is None:
            ERROR("storage init faild!")

    def _init_speaker(self):
        INFO("initlizing speaker...")
        self._spk = Text2Speech()

    def _init_audio_server(self):
        Sound.AUDIO_SERVER_ADDRESS = self._init_res["connection"]["audio_server"]
        INFO("connect to audio server: %s " % (Sound.AUDIO_SERVER_ADDRESS))

    def _init_cmd_socket(self):
        cmd_bind_port = self._init_res["connection"]["cmd_bind_port"]
        INFO("initlizing cmd socket, bing to:" + cmd_bind_port)

        self._cmd_bind_port = cmd_bind_port

    def _init_helper(self):
        publisher_ip = self._init_res["connection"]["publisher"]
        heartbeat_port = self._init_res["connection"]["heartbeat_port"]
        INFO("init message publisher: %s, heartbeat port: %s" %
                                            (publisher_ip, heartbeat_port))
        self._msg_sender = MessageHelper(publisher_ip, heartbeat_port)

        switch_scan = SwitchHelper.BOARDCAST_ADDRESS
        INFO("init switch scan: " + switch_scan)
        self._switch = SwitchHelper()

        INFO("init ril helper")
        self._ril = RilHelper()

        INFO("init sensor helper")
        self._sensor = SensorHelper()

        tag_server_ip = self._init_res["connection"]["tag_server"]
        INFO("init tag server. %s" % tag_server_ip)
        self._tag = TagHelper(tag_server_ip, self._init_res["tag"])

        ping_server_ip = self._init_res["connection"]["ping_server"]
        INFO("init ping server. %s" % ping_server_ip)
        self._ping = PingHelper(ping_server_ip, self._init_res["ping"])

        geo_server_ip = self._init_res["connection"]["geo_fencing_server"]
        INFO("init geo-fencing server. %s" % geo_server_ip)
        self._geo = GeoFencingHelper(geo_server_ip)

    def _cmd_begin_callback(self, command):
        DEBUG("command begin: %s" % (command))
        # self.publish_msg(command, u"执行: " + command)

    def _cmd_end_callback(self, command):
        DEBUG("command end: %s" % (command))
        # self.publish_msg(command, "end: " + command)

    def publish_msg(self, sub_id, msg, cmd_type="normal"):
        self._msg_sender.publish_msg(sub_id, msg, cmd_type)

    def parse_cmd(self, cmd, persist=True):
        if not self._resume:
            timestamp = int(time.time())
            if cmd.startswith("@"):
                cmd = cmd[1:]
                if persist is True:
                    self._storage.rpush(
                            "lehome:cmd_location_list",
                            "%d:%s" % (timestamp, cmd)
                            )
                self.publish_msg(cmd, cmd, cmd_type="bc_loc")
            elif cmd.startswith("^"):
                cmd = cmd[1:]
                if persist is True:
                    self._storage.rpush(
                            "lehome:cmd_geo_location_list",
                            "%d:%s" % (timestamp, cmd)
                            )
                self._geo.send_geo_report(cmd)
            else:
                INFO("parse_cmd: " + cmd)
                if persist is True:
                    self._storage.rpush(
                            "lehome:cmd_history_list",
                            "%d:%s" % (timestamp, cmd)
                            )
                self.runtime.parse(cmd)

    def activate(self):
        Sound.notice(Res.get_res_path("sound/com_begin"))
        self._spk.start()
        self.runtime.resume_parsing()

        application = tornado.web.Application([
            (r"/home/cmd", CmdHandler, dict(home=self)),
        ])
        application.listen(self._cmd_bind_port.encode("utf-8"))
        tornado.ioloop.PeriodicCallback(try_exit, 1000).start()
        tornado.ioloop.IOLoop.instance().start()
        INFO("home activate!")

    def setResume(self, resume):
        self._resume = resume

class CmdHandler(tornado.web.RequestHandler):
    def initialize(self, home):
        self.home = home

    def post(self):
        cmd = self.get_argument("cmd", default=None, strip=False)
        if cmd is None:
            self.write("error")
            return
        # INFO("get cmd through http post:%s", cmd)
        if cmd.count('#')%2 == 0:
            self.home.parse_cmd(cmd)
            self.write("ok")
        else:
            WARN("unmatch '%s'." % "#")
            self.write("ok")
            self.home.publish_msg("error", u"%s不匹配" % "#")

is_closing = False
def signal_handler(signum, frame):
    global is_closing
    is_closing = True


def try_exit():
    global is_closing
    if is_closing:
        # clean up here
        tornado.ioloop.IOLoop.instance().stop()
        logging.info('exit success')

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)

    home = Home()
    home.activate()
    WARN("home got exception, now exit.")
