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
from util.thread import TimerThread
from util.Res import Res
from util.log import *


class RilHelper:

    SOCKET_TIMEOUT = 3
    RETRY_TIME = 3
    RIL_PORT = 60000

    def __init__(self):
        init_json = Res.init("init.json")
        self._address = init_json["ril_address"]
        self._send_lock = threading.Lock()

    def send_cmd(self, cmd):
        return self._send_cmd(self._address, cmd)

    def _get_switch_cmd(self, action):
        return "%s" % action

    def _send_cmd(self, target_ip, cmd):
        if target_ip is None or len(target_ip) == 0:
            ERROR("invaild ril_ip.")
            return
        if cmd is None or len(cmd) == 0:
            ERROR("empty ril cmd.")
            return

        with self._send_lock:
            INFO("ril send command:%s to:%s:%s"
                    % (cmd, target_ip, RilHelper.RIL_PORT))
            for i in range(0, RilHelper.RETRY_TIME):
                try:
                    # sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    # server_address = (target_ip, RilHelper.RIL_PORT)  
                    # sock.connect(server_address)
                    sock = socket.create_connection(
                            (target_ip, RilHelper.RIL_PORT),
                            RilHelper.SOCKET_TIMEOUT)
                    time.sleep(0.5)
                    sock.send(cmd)
                    recv = sock.recv(512)
                    sock.close()

                    INFO("ril recv:%s" % recv)
                    return recv.strip()
                except socket.timeout:
                    ERROR("RilHelper cmd socket timeout.")
                except Exception, ex:
                    ERROR(ex)
            return None
