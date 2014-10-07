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


import os
import threading
import time
import subprocess
import json
from Queue import Queue, Empty
import collections
import logging
import zmq

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')

DEBUG = logging.debug
INFO = logging.info
WARN = logging.warning
ERROR = logging.error
CRITICAL = logging.critical


class tag_endpoint(object):

    # tag 的蓝牙地址
    tag_addrs = ["E2C56DB5-DFFB-48D2-B060-D0F5A71096E0"]

    def __init__(self, name):
        self.server_ip = "tcp://*:8006"
        self.name = name
        self.tags = {}
        self._queue = Queue()
        self._init_fliter()

    def _init_fliter(self):
        self.fliter = {}
        N = 5.0
        A = 1.0
        for tag_addr in tag_endpoint.tag_addrs:
            self.fliter[tag_addr] = {}
            self.fliter[tag_addr]['N'] = N
            self.fliter[tag_addr]['A'] = A
            self.fliter[tag_addr]['S'] = \
                    self.fliter[tag_addr]['N']*self.fliter[tag_addr]['A']
            self.fliter[tag_addr]['queue'] = collections.deque([1]*10, maxlen=10)

    # 网上找的一个计算距离的公式，不太准
    def calDistance(self, txPower, rssi):
        if rssi == 0:
            return 0.0

        ratio = rssi*1.0/txPower
        if ratio < 1.0:
            return ratio**10
        else:
            accuracy = 0.89976*(ratio**7.7095) + 0.111
            return accuracy

    # 窗口长度为10，去除最高和最低值后，减去上一次的平均值再加上窗口的平均值
    def rssi_fliter(self, addr, rssi):
        if addr not in self.fliter:
            return -1
        fliter = self.fliter[addr]
        if fliter is None:
            return -1

        fliter['queue'].append(rssi)
        ordered_queue = list(fliter['queue'])
        ordered_queue.sort()
        ordered_queue = ordered_queue[1:-1]
        C = sum(ordered_queue)/len(ordered_queue)

        fliter['S'] = fliter['S'] - fliter['A'] + C
        fliter['A'] = fliter['S']/fliter['N']
        return fliter['A']

    # 依赖于ibeacon_scan这个bash脚本
    def _fetch_rssi(self):
        subprocess.call(
                        ["sudo", "killall", "-9", "hcitool"],
                        )
        subprocess.call(
                        ["./vender/ibeacon_scan"],
                        )
        proc = subprocess.Popen(
                                ["./vender/ibeacon_scan", "-b"],
                                stdout=subprocess.PIPE)
        while True :
            try:
                data = proc.stdout.readline() #block / wait
                # print data
                if data == "":
                    print "no broadcast data."
                    break
                datas = data.split()
                addr = datas[0]
                if addr in tag_endpoint.tag_addrs:
                    # 将收集的数据放进缓冲队列里
                    self._queue.put(datas)
            except Exception, ex:
                ERROR(ex)
                time.sleep(3)

    def _parse_rssi(self):
        while True:
            try:
                # 从缓冲队列里取出数据
                queue = self._queue
                datas = queue.get(timeout=10)
                addr = datas[0]
                queue.task_done()

                txPower = int(datas[3])
                rssi = int(datas[4])
                rssi = self.rssi_fliter(addr, rssi)
                self.tags[addr] = self.calDistance(txPower, rssi)
            except Empty:
                self.tags[addr] = -1.0
                INFO('parse rssi timeout.')
            except Exception, ex:
                self.tags[addr] = -1.0
                ERROR(ex)
                time.sleep(3)
            INFO("addr:%s, distance:%f" % (addr, self.tags[addr]))

    def start(self):

        INFO("start tag server...")
        INFO("bind to" + self.server_ip)

        fetch_t = threading.Thread(
                    target=self._fetch_rssi
                    )
        fetch_t.daemon = True
        fetch_t.start()

        parse_t = threading.Thread(
                    target=self._parse_rssi
                    )
        parse_t.daemon = True
        parse_t.start()

        context = zmq.Context()
        self.socket = context.socket(zmq.REP)
        self.socket.setsockopt(zmq.LINGER, 0)
        self.socket.bind(self.server_ip)
        time.sleep(0.5)

        while True:
            try:
                poller = zmq.Poller()
                poller.register(self.socket, zmq.POLLIN | zmq.POLLOUT)
                if poller.poll(5*1000):
                    req = self.socket.recv_string()
                    # rep = "%s#%s" % (self.name, str(self.distance))
                    rep = {"res": "error"}
                    if req in tag_endpoint.tag_addrs:
                        distance = self.tags[req]
                        status = "unknown" if distance < 0 else "normal"
                        rep = {"res":
                                {
                                    "name": self.name,
                                    "distance": distance,
                                    "status": status,
                                }
                                }
                    self.socket.send_string(json.dumps(rep))
                    INFO("recv req:" + req)
            except (KeyboardInterrupt, SystemExit):
                self.socket.close()
                self.stop()
                raise
            except Exception, ex:
                ERROR(ex)
                time.sleep(3)

    def stop(self):
        subprocess.call(
                        ["sudo", "killall", "-9", "hcitool"],
                        )
        print "tag_endpoint stop."

if __name__ == '__main__':
    tag_endpoint("test").start()
