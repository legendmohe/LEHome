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
import zmq
from util.Res import Res
from util.log import *

class TagHelper(object):
    def __init__(self, name_to_place_ip, name_to_addr):
        self._name_to_place_ip = name_to_place_ip
        self._name_to_addr = name_to_addr

    def addr_for_name(self, name):
        if name in self._name_to_addr:
            return self._name_to_addr[name]
        else:
            return None

    def place_ip_for_name(self, name):
        if name in self._name_to_place_ip:
            return self._name_to_place_ip[name]
        else:
            return None

    def near(self, addr, place_ip):
        rep = self._send_request(addr, place_ip)
        if rep is None:
            return None
        res = json.loads(rep)["res"]
        if res == "error":
            INFO('tag server error.')
            return None
        distance = res['distance']
        return True if distance > 0.0 else False

    def _send_request(self, addr, place_ip):
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.LINGER, 0)
        socket.connect(place_ip)
        socket.send_string(addr)
        rep = None
        try:
            poller = zmq.Poller()
            poller.register(socket, zmq.POLLIN)
            if poller.poll(5*1000):
                rep = socket.recv_string()
                DEBUG("recv msgs:" + rep)
        except:
            WARN("socket timeout.")
        return rep
