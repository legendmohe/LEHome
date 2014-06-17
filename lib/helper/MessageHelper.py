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

    def _msg_worker(self):
        while True:
            msg_string = self._get_msg()
            self._pub_sock.send_string(msg_string)

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
            msg_string = json.dumps({"type": cmd_type, "msg": msg})
            # INFO("public msg:" + msg_string)
            self._put_msg(msg_string)
