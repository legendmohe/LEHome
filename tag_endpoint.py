#!/usr/bin/env python
# encoding: utf-8

import os
import threading
import time
import subprocess
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

    def __init__(self, name):
        self.server_ip = "tcp://*:8006"
        self.name = name

        self.N = 5
        self.A = 1.0
        self.S = self.N*self.A
        self.distance = 0.0
        self.fliter_queue = collections.deque([1]*10, maxlen=10)

    def calDistance(self, txPower, rssi):
        if rssi == 0:
            return 0.0

        ratio = rssi*1.0/txPower
        if ratio < 1.0:
            return ratio**10
        else:
            accuracy = 0.89976*(ratio**7.7095) + 0.111
            return accuracy

    def rssi_fliter(self, rssi):
        print rssi
        self.fliter_queue.append(rssi)
        ordered_queue = list(self.fliter_queue)
        ordered_queue.sort()
        ordered_queue = ordered_queue[1:-1]
        data = sum(ordered_queue)/len(ordered_queue)
        self.S = self.S - self.A + data
        self.A = self.S/self.N
        return self.A

    def _parse_rssi(self):
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
                if data == "":
                    print "no broadcast data."
                    break
                datas = data.split()
                txPower = int(datas[3])
                rssi = int(datas[4])
                rssi = self.rssi_fliter(rssi)
                self.distance = self.calDistance(txPower, rssi)
                INFO("distance:%f" % (self.distance, ))
            except Exception, ex:
                ERROR(ex)
                break

    def start(self):

        INFO("start tag server...")
        INFO("bind to" + self.server_ip)

        tag_t = threading.Thread(
                    target=self._parse_rssi
                    )
        tag_t.daemon = True
        tag_t.start()

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
                    rep = "%s#%s" % (self.name, str(self.distance))
                    self.socket.send_string(rep)
                    INFO("recv req:" + req)
            except (KeyboardInterrupt, SystemExit):
                self.socket.close()
                self.stop()
                raise
            except:
                WARN("socket timeout.")

    def stop(self):
        subprocess.call(
                        ["sudo", "killall", "-9", "hcitool"],
                        )
        print "tag_endpoint stop."

if __name__ == '__main__':
    tag_endpoint("test").start()
