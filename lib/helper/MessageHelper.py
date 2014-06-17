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

    def __init__(self, pub_address):
        self.pub_address = pub_address
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
        self._sequence_num = 0
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

    def _put_msg(self, msg):
        self._msg_queue.put(msg)

    def _get_msg(self):
        msg = self._msg_queue.get(
                                block=True,
                                ) # block!
        return msg

    def _init_pub_heartbeat(self):
        def heartbeat():
            self.publish_msg(None, "", "heartbeat")
        self.timer = TimerThread(interval=20, target=heartbeat)
        self.timer.start()

    def _init_worker(self):
        self.worker_thread = threading.Thread(target=self._msg_worker)
        self.worker_thread.daemon = True
        self.worker_thread.start()

    def publish_msg(self, sub_id, msg, cmd_type="normal"):
        with self._msg_lock:
            msg_dict = {"type": cmd_type, "msg": msg}
            # INFO("public msg:" + msg_string)

            if cmd_type != "heartbeat":
                self._sequence_num += 1
                msg_dict["seq"] = self._sequence_num
                msg_string = json.dumps(msg_dict)
                self._backup_dict[self._sequence_num] = (
                                            msg_string, len(self._subscribers))
            else:
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
        return self._sequence_num
