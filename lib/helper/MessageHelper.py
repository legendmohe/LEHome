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
import socket
import pickle
import time
import json
import zmq
from Queue import Queue, Empty
from util.Res import Res
from util.log import *
from util.thread import TimerThread


class MessageHelper(object):
    
    LOCAL_HEARTBEAT_RATE = 5
    MESSAGE_DB = "./data/msg.pcl"

    def __init__(self, pub_address, hb_port):
        self.pub_address = pub_address
        self.heartbeat_port = int(hb_port)
        self._data_lock = threading.Lock()
        self._msg_lock = threading.Lock()
        self._msg_queue = Queue()

        self._init_data()
        self._init_pub_heartbeat()
        self._init_worker()

    def _init_data(self):
        self._load_data()
        if 'seq' not in self._context:
            self._context['seq'] = 1

    def _load_data(self):
        self._context = {}
        with self._data_lock:
            try:
                with open(MessageHelper.MESSAGE_DB, "rb") as f:
                    self._context = pickle.load(f)
            except:
                INFO("empty todo list.")
        return self._context

    def _save_data(self):
        with self._data_lock:
            try:
                with open(MessageHelper.MESSAGE_DB, "wb") as f:
                    pickle.dump(self._context, f, True)
            except Exception, e:
                ERROR(e)
                ERROR("invaild MessageHelp data path:%s", MessageHelper.MESSAGE_DB)

    def _msg_worker(self):
        context = zmq.Context()
        publisher = self.pub_address
        _pub_sock = context.socket(zmq.PUB)
        INFO("pub bind to : %s " % (publisher))
        _pub_sock.bind(publisher)
        self._pub_sock = _pub_sock

        #  for sending init string too fast
        time.sleep(0.5)
        while True:
            msg_string = self._get_msg()
            self._pub_sock.send_string(msg_string)
            time.sleep(0.3)

    def _put_msg(self, msg):
        self._msg_queue.put(msg)

    def _get_msg(self):
        msg = self._msg_queue.get(
                                block=True,
                                ) # block!
        self._msg_queue.task_done()
        return msg

    def _init_pub_heartbeat(self):
        if self.heartbeat_port is None or self.heartbeat_port == 0:
            WARN("heartbeat port is invalid. heartbeat is disabled")
            return

        def heartbeat():
            self.publish_msg(None, "", "heartbeat")
        timer = TimerThread(interval=20, target=heartbeat)
        timer.start()

        local_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        local_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, True)
        local_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        def local_heartbeat():
            address = ("255.255.255.255", self.heartbeat_port)
            local_sock.sendto("ok", address)

        local_heartbeat_thread = TimerThread(
                            interval=MessageHelper.LOCAL_HEARTBEAT_RATE,
                            target=local_heartbeat
                            )
        local_heartbeat_thread.start()

    def _init_worker(self):
        self._msg_thread = threading.Thread(target=self._msg_worker)
        self._msg_thread.daemon = True
        self._msg_thread.start()

    def publish_msg(self, sub_id, msg, cmd_type="normal"):
        msg_dict = {
                    "type": cmd_type,
                    "msg": msg,
                    "ts": "%d" % int(time.time()),
                   }
        with self._msg_lock:
            if cmd_type != "heartbeat":
                self._context['seq'] += 1
                msg_dict["seq"] = self._context['seq']
                msg_string = json.dumps(msg_dict)
                DEBUG("push msg:%s-%s-%s" % (self._context['seq'], cmd_type, msg))
            else:
                msg_dict["seq"] = -1
                msg_string = json.dumps(msg_dict)
            self._put_msg(msg_string)
            self._save_data()

    def cur_seq(self):
        return self._context['seq']
