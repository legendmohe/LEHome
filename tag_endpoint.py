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
import json
from Queue import Queue, Empty
import collections
import logging

import zmq
import paho.mqtt.client as mqtt

from util.log import *


class tag_endpoint(object):

    TAG_TIMEOUT = 5

    # tag 的蓝牙地址
    tag_addrs = [
                "E2C56DB5DFFB48D2B060D0F5A71096E0",
                "FDA50693A4E24FB1AFCFC6EB07647825"
                ]

    sniffer_ids = [
                    "F4B85E03F44D",
                    ]

    def __init__(self):
        self.server_ip = "tcp://*:8006"
        self.tags = {}
        self._queues = {}
        self._filter = {}
        self._init_filter()

    def _init_filter(self):
        N = 1.0 # 划动平均
        A = 1.0
        for sniffer_id in tag_endpoint.sniffer_ids:
            sniffer = {}
            for tag_addr in tag_endpoint.tag_addrs:
                tag = {}
                tag['N'] = N
                tag['A'] = A
                tag['S'] = tag['N']*tag['A']
                tag['queue'] = collections.deque([255]*10, maxlen=10)
                sniffer[tag_addr] = tag
            self._filter[sniffer_id] = sniffer

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
    def rssi_filter(self, sniffer_id, addr, rssi):
        if sniffer_id not in self._filter:
            return -1

        sniffer = self._filter[sniffer_id]
        if addr not in sniffer or sniffer[addr] is None:
            return -1

        tag = sniffer[addr]
        tag['queue'].append(rssi)
        ordered_queue = list(tag['queue'])
        ordered_queue.sort()
        ordered_queue = ordered_queue[1:-1]
        C = sum(ordered_queue)/len(ordered_queue)

        tag['S'] = tag['S'] - tag['A'] + C
        tag['A'] = tag['S']/tag['N']
        return tag['A']

    def _on_sniffer_connect(self, client, userdata, flags, rc):
        # print("Connected with result code "+str(rc))
        client.subscribe("/beacons")

    def _on_rssi_message(self, client, userdata, msg):
        # print(msg.topic+" "+str(msg.payload))
        try:
            data = json.loads(msg.payload)
        except Exception, ex:
            INFO(ex)
            return
        sniffer_id = data["id"]
        beacons = data["raw_beacons_data"].split(";")
        for raw in beacons:
            beacon = self._str_to_beacon_item(raw)
            if beacon is not None \
                   and sniffer_id in self._queues \
                   and beacon['uuid'] in self._queues[sniffer_id]:
                # 将收集的数据放进缓冲队列里
                self._queues[sniffer_id][beacon["uuid"]].put(beacon)
                print "sniffer:", sniffer_id, "beacon:", beacon
                DEBUG("sniffer:%s, beacon:%s" % (sniffer_id, str(beacon)))

    def _fetch_rssi(self):
        client = mqtt.Client()
        client.on_connect = self._on_sniffer_connect
        client.on_message = self._on_rssi_message
        client.connect("localhost", 1883, 60)
        client.loop_forever()

    def _parse_rssi(self, sniffer_id, addr):
        queue = self._queues[sniffer_id][addr]
        if sniffer_id not in self.tags:
            self.tags[sniffer_id] = {}
        tag = self.tags[sniffer_id]
        tag[addr] = -1.0
        txPower = 197
        while True:
            try:
                # 从缓冲队列里取出数据
                beacon = queue.get(timeout=tag_endpoint.TAG_TIMEOUT)
                queue.task_done()
                addr = beacon["uuid"]
                txPower = beacon["power"]
                rssi = self.rssi_filter(sniffer_id, addr, beacon["rssi"])
                tag[addr] = self.calDistance(txPower, rssi)
            except Empty:
                rssi = self.rssi_filter(sniffer_id, addr, 255)
                tag[addr] = self.calDistance(txPower, rssi)
                DEBUG('parse %s timeout.' % addr)
            except (KeyboardInterrupt, SystemExit):
                self.socket.close()
                self.stop()
                raise
            except Exception, ex:
                tag[addr] = -1.0
                ERROR(ex)
                TRACE_EX()
                time.sleep(3)
            DEBUG("sniffer:%s, addr:%s, distance:%f"\
                    % (sniffer_id, addr, tag[addr]))
            print "sniffer:%s, addr:%s, distance:%f"\
                    % (sniffer_id, addr, tag[addr])

    def _str_to_beacon_item(self, src):
        if src is None or len(src) == 0:
            return None
        result = {}
        delta = 0
        result["mac"] = src[:delta + 12]
        delta += 12
        result["uuid"] = src[delta:delta + 32]
        delta += 32
        result["major"] = src[delta:delta + 4]
        delta += 4
        result["minor"] = src[delta:delta + 4]
        delta += 4
        result["power"] = int(src[delta:delta + 2], 16)
        delta += 2
        result["bettery"] = int(src[delta:delta + 2], 16)
        delta += 2
        result["rssi"] = int(src[delta:delta + 2], 16)
        delta += 2
        return result

    def start(self):

        INFO("start tag server...")
        INFO("bind to" + self.server_ip)

        fetch_t = threading.Thread(
                    target=self._fetch_rssi
                    )
        fetch_t.daemon = True
        fetch_t.start()

        # 当其中一个ibeacon广播超时的时候，要在程序里标记这个状态。若只用一个
        # 线程来统一处理接受到的广播包，那么对某一个ibeacon的超时检测的逻辑就
        # 会比较复杂。所以分开几条线程来处理，每条线程负责管理某个ibeacon的状态
        for sniffer_id in tag_endpoint.sniffer_ids:
            self._queues[sniffer_id] = {}
            for addr in tag_endpoint.tag_addrs:
                self._queues[sniffer_id][addr] = Queue() #  queue for each tag
                parse_t = threading.Thread(
                            target=self._parse_rssi,
                            args=(sniffer_id, addr, )
                            )
                parse_t.daemon = True
                parse_t.start()

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
                    req = self.socket.recv_string().split(",")
                    rep = {"res": "error"}
                    if req[0] in tag_endpoint.sniffer_ids \
                        and req[1] in tag_endpoint.tag_addrs:
                        distance = self.tags[req[0]][req[1]]
                        status = "unknown" if distance < 0 else "normal"
                        rep = {"res":
                                {
                                    "distance": distance,
                                    "status": status,
                                }
                                }
                    self.socket.send_string(json.dumps(rep))
                    DEBUG("recv req:" + str(req))
            except (KeyboardInterrupt, SystemExit):
                self.socket.close()
                self.stop()
                raise
            except Exception, ex:
                ERROR(ex)
                self.socket.close()
                poller.unregister(self.socket)
                self.socket = None
                time.sleep(3)

    def stop(self):
        INFO("tag_endpoint stop.")

if __name__ == '__main__':
    tag_endpoint().start()
