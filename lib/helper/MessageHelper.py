#!/usr/bin/env python
# encoding: utf-8


import threading
import time
import json
import zmq
from Queue import Queue, Empty
from util.log import *
from util.thread import TimerThread


class MessageHelper(object):

    def __init__(self, pub_address, cmd_address):
        self.pub_address = pub_address
        self.cmd_address = cmd_address
        self._msg_lock = threading.Lock()
        self._msg_queue = Queue()

        self._init_subscriber()
        self._init_publisher()

    def _init_publisher(self):
        context = zmq.Context()
        publisher = self.pub_address
        _pub_sock = context.socket(zmq.PUB)
        INFO("pub bind to : %s " % (publisher))
        _pub_sock.bind(publisher)
        self._pub_sock = _pub_sock

        #  for sending init string too fast
        time.sleep(0.5)

        self._init_pub_heartbeat()
        self._init_worker()

    def _init_subscriber(self):
        self._backup_dict = {}
        self._seq_num = 0
        self._subscribers = set()

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
        while True:
            msg_string = self._get_msg()
            self._pub_sock.send_string(msg_string)
            self._msg_queue.task_done()

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
                res_string = json.dumps({"res": "ok", "maxseq": self._seq_num})
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
        self.timer = TimerThread(interval=20, target=heartbeat)
        self.timer.start()

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
                self._seq_num += 1
                msg_dict["seq"] = self._seq_num
                msg_dict["maxseq"] = self._seq_num
                msg_string = json.dumps(msg_dict)
                self._backup_dict[self._seq_num] = (
                                            msg_string, len(self._subscribers))
            else:
                msg_dict["seq"] = -1
                msg_dict["maxseq"] = self._seq_num
                msg_string = json.dumps(msg_dict)
            self._put_msg(msg_string)

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
        return self._seq_num
