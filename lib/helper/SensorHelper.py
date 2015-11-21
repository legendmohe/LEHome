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


import threading
import json
import time
import socket
# import urllib
# import urllib2
# import zmq
from util.Res import Res
from util.log import *


class SensorHelper:
    TYPE_TEMP = "T"
    TYPE_HUM = "H"
    TYPE_PIR = "P"
    TYPE_LUM = "L"
    TYPE_ALL = "A"

    def __init__(self):
        self._sock = None
        init_json = Res.init("init.json")
        try:
            self.place2ip = init_json["sensor"]
        except Exception, e:
            ERROR(e)
            ERROR("invaild SensorHelper init json.")
            self.place2ip = {}

        self._send_lock = threading.Lock()

    def get_places(self):
        if self.place2ip is None:
            return None
        return self.place2ip.keys()

    def addr_for_place(self, place):
        return self.place2ip.get(place, None)

    def place_for_addr(self, addr):
        for place in self.place2ip:
            if self.place2ip[place] == addr:
                return place
        return None

    def get_all(self, target_addr):
        return self.get_sensor_value(target_addr, SensorHelper.TYPE_ALL)

    def get_temp(self, target_addr):
        return self.get_sensor_value(target_addr, SensorHelper.TYPE_TEMP)

    def get_humidity(self, target_addr):
        return self.get_sensor_value(target_addr, SensorHelper.TYPE_HUM)

    def get_pir(self, target_addr):
        return self.get_sensor_value(target_addr, SensorHelper.TYPE_PIR)

    def get_brightness(self, target_addr):
        lig = self.get_sensor_value(target_addr, SensorHelper.TYPE_LUM)
        return lig

    def get_sensor_value(self, addr, cmd):
        try:
            addr, port = addr.split(":")
            port = int(port)
        except Exception, e:
            ERROR(e)
            ERROR("invaild place address format: %s" % addr)
        rep = self.send_cmd(addr, port, cmd)
        return rep

    def send_cmd(self, addr, port, cmd):
        if cmd is None or len(cmd) == 0:
            ERROR("invaild sensor cmd.")
            return
        DEBUG("sending cmd to place: %s:%d %s" % (addr, port, cmd))

        rep = ""
        with self._send_lock:
            # import pdb
            # pdb.set_trace()
            # if self._sock is None:
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.settimeout(5)
            self._sock.connect((addr, port))
            try:
                self._sock.send(cmd)
                rep = self._sock.recv(2048)
                DEBUG("place rep:" + rep)
            except Exception, ex:
                ERROR(ex)
                ERROR("can't connect to place.")
            self._sock.close()
            self._sock = None
        return rep

    def readable(self, src, cmd_type):
        if src is None or len(src) == 0:
            return ""
        try:
            if cmd_type == SensorHelper.TYPE_TEMP:
                return u"温度:%s℃" % src
            elif cmd_type == SensorHelper.TYPE_HUM:
                return u"湿度:%s%%" % src
            elif cmd_type == SensorHelper.TYPE_PIR:
                return u"是否有人:%s" % u'否' if src == "0" else u'是'
            elif cmd_type == SensorHelper.TYPE_LUM:
                return u"光照:%s" % src
            elif cmd_type == SensorHelper.TYPE_ALL:
                data = src.split(",")
                ret = u"温度:%s℃, 湿度:%s%%" \
                          % (
                             data[0],
                             data[1],
                            )
                # ret = u"温度:%s℃, 湿度:%s%%, 是否有人:%s, 光照:%s" \
                #           % (
                #              data[0],
                #              data[1],
                #              (u'否' if data[2] == "0" else u'是'),
                #              data[3]
                #             )
                return ret
        except Exception, ex:
            ERROR(ex)
            ERROR("invaild readable src:%s" % src)
            return ""
