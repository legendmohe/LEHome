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
from util.log import *
from util.thread import TimerThread


class MessageHelper(object):

    LOCAL_SCAN_PORT = 9002
    LOCAL_HEARTBEAT_RATE = 2
    MESSAGE_DB = "./data/msg.pcl"

    def __init__(self, pub_address, cmd_address):
        self.pub_address = pub_address
        self.cmd_address = cmd_address
        self._data_lock = threading.Lock()
        self._msg_lock = threading.Lock()
        self._msg_queue = Queue()

        self._init_data()
        self._init_subscriber()
        self._init_pub_heartbeat()
        self._init_worker()

    def _init_data(self):
        self._load_data()
        if 'seq' not in self._context:
            self._context['seq'] = 1

    def _init_subscriber(self):
        self._backup_dict = {}
        self._subscribers = set()

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

    def add_subscribers(self, new_sub):
        if new_sub is Null or len(new_sub) == 0:
            ERROR("invaild subscriber.")
            return False
        self._subscribers.add(new_sub)
        return True

    def remove_subscribers(self, old_sub):
        if old_sub is Null or len(old_sub) == 0:
            ERROR("invaild subscriber.")
            return False
        self._subscribers.remove(old_sub)
        return True

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

    def _cmd_worker(self):
        context = zmq.Context()
        socket = context.socket(zmq.REP)
        socket.bind(self.cmd_address)
        while True:
            cmd = socket.recv_string()
            res = self._handle_cmd(cmd)
            socket.send_string(res)

    def _put_msg(self, msg):
        self._msg_queue.put(msg)

    def _get_msg(self):
        msg = self._msg_queue.get(
                                block=True,
                                ) # block!
        self._msg_queue.task_done()
        return msg

    def _handle_cmd(self, cmd):
        try:
            cmd_object = json.loads(cmd)
            cmd_type = cmd_object["type"]
            if cmd_type == "load":
                cmd_from = cmd_object["from"]
                cmd_to = cmd_object["to"]
                msgs = self.msg_for_range(cmd_from, cmd_to)
                res_string = json.dumps({"res": msgs})
            elif cmd_type == "login":
                user_id = cmd_object["id"]
                self.add_subscribers(user_id)
                res_string = json.dumps({"res": "ok", "maxseq": self._context['seq']})
            elif cmd_type == "logout":
                user_id = cmd_object["id"]
                self.remove_subscribers(user_id)
                res_string = json.dumps({"res": "ok"})
            elif cmd_type == "done":
                seq = cmd_object["seq"]
                self.done_msg(seq)
                res_string = json.dumps({"res": "ok"})
        except Exception, e:
            ERROR(e)
            res_string = json.dumps({"res": "error"})
        return res_string

    def _init_pub_heartbeat(self):
        def heartbeat():
            self.publish_msg(None, "", "heartbeat")
        timer = TimerThread(interval=20, target=heartbeat)
        timer.start()

        local_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        local_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, True)
        local_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        def local_heartbeat():
            address = ("255.255.255.255", MessageHelper.LOCAL_SCAN_PORT)
            local_sock.sendto("ok", address)

        local_heartbeat_thread = TimerThread(
                            interval=MessageHelper.LOCAL_HEARTBEAT_RATE,
                            target=local_heartbeat
                            )
        local_heartbeat_thread.start()

    def _init_worker(self):
        self._cmd_thread = threading.Thread(target=self._cmd_worker)
        self._cmd_thread.daemon = True
        self._cmd_thread.start()

        self._msg_thread = threading.Thread(target=self._msg_worker)
        self._msg_thread.daemon = True
        self._msg_thread.start()

    def publish_msg(self, sub_id, msg, cmd_type="normal"):
        with self._msg_lock:
            msg_dict = {
                            "type": cmd_type,
                            "msg": msg
                        }
            # INFO("public msg:" + msg_string)

            if cmd_type != "heartbeat":
                self._context['seq'] += 1
                msg_dict["seq"] = self._context['seq']
                msg_dict["maxseq"] = self._context['seq']
                msg_string = json.dumps(msg_dict)
                if len(self._subscribers) > 0:
                    self._backup_dict[self._context['seq']] = (
                                            msg_string, len(self._subscribers))
            else:
                msg_dict["seq"] = -1
                msg_dict["maxseq"] = self._context['seq']
                msg_string = json.dumps(msg_dict)
            self._put_msg(msg_string)
            self._save_data()

    def done_msg(self, seq):
        if seq in self._backup_dict:
            item = self._backup_dict[seq]
            item[1] -= 1
            if item[1] == 0:
                del self._backup_dict[seq]
        else:
            WARN("no such seq:" + str(seq))

    def msg_for_range(self, begin_seq, end_seq):
        msgs = []
        for seq in range(begin_seq, end_seq + 1):
            if seq in self._backup_dict:
                msg, _ = self._backup_dict[seq]
                msg.append(msg)
        return msgs

    def cur_seq(self):
        return self._context['seq']
