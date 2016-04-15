#!/usr/bin/env python
# encoding: utf-8

# Copyright 2010 Xinyu, He <legendmohe@foxmail.com>
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
import os
import signal
import time
import subprocess
import errno
import json
from Queue import Queue, Empty
import collections
import logging

import zmq
import ping

from util.log import *
from util.Res import Res


class ping_endpoint(object):

    PING_INTERVAL = 10
    TIMEOUT = 0.8

    def __init__(self):
        self.devices = {}
        self._queues = {}

        settings = Res.init("init.json")
        self.server_ip = "tcp://*:8005"
        self._device_addrs = []
        addrs = settings['ping']['device']
        for name in addrs:
            self._device_addrs.append(addrs[name])

    def _do_ping(self, addr):
        while True:
            try:
                self.devices[addr] = self._ping(addr)
                print "device:", addr, "online", self.devices[addr]
                DEBUG("device:%s online:%d" % (addr, self.devices[addr]))

                time.sleep(ping_endpoint.PING_INTERVAL)
            except (KeyboardInterrupt, SystemExit):
                self.stop()
                raise
            except Exception, ex:
                ERROR(ex)
                TRACE_EX()
                time.sleep(3)

    def _timeout(self, proc):
        print "timeout!"
        if proc.poll() is None:
            try:
                proc.terminate()
                INFO('Error: process taking too long to complete--terminating')
            except OSError as e:
                if e.errno != errno.ESRCH:
                    raise

    def _ping(self, addr):
        cmd = "ping -c %d -W %.1f %s > /dev/null 2>&1" % (10, ping_endpoint.TIMEOUT, addr)
        proc_timeout = 10*ping_endpoint.TIMEOUT + 5
        proc = subprocess.Popen(cmd, shell=True)

        try:
            t = threading.Timer(proc_timeout, self._timeout, [proc])
            t.start()
            proc.wait()
            DEBUG("ping return code:%d" % proc.returncode)
            t.cancel()
            t.join()
        except Exception, ex:
            print ex
            proc.terminate()
        return True if proc.returncode == 0 else False

    def start(self):

        INFO("start ping server...")
        INFO("bind to" + self.server_ip)

        for addr in self._device_addrs:
            INFO("load ping device:" + addr)
            self.devices[addr] = False
            ping_t = threading.Thread(
                        target=self._do_ping,
                        args=(addr, )
                        )
            ping_t.daemon = True
            ping_t.start()

        context = zmq.Context()
        poller = zmq.Poller()
        self.socket = None
        time.sleep(0.5)

        while True:
            if self.socket is None:
                self.socket = context.socket(zmq.REP)
                self.socket.setsockopt(zmq.LINGER, 0)
                self.socket.bind(self.server_ip)
                poller.register(self.socket, zmq.POLLIN | zmq.POLLOUT)
            try:
                if poller.poll(5*1000):
                    req = self.socket.recv_string()
                    rep = {"res": "error"}
                    if req in self._device_addrs:
                        state = self.devices[req]
                        rep = {"res":
                                  {
                                      "online": state,
                                  }
                              }
                    self.socket.send_string(json.dumps(rep))
                    DEBUG("recv req:" + str(req))
            except (KeyboardInterrupt, SystemExit):
                self.socket.close()
                poller.unregister(self.socket)
                self.socket = None
                self.stop()
                raise
            except Exception, ex:
                ERROR(ex)
                self.socket.close()
                poller.unregister(self.socket)
                self.socket = None
                time.sleep(3)

    def stop(self):
        INFO("ping_endpoint stop.")

if __name__ == '__main__':
    ping_endpoint().start()
