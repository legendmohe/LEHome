#!/usr/bin/env python
# encoding: utf-8


import threading
import time
import json
import zmq
import serial
from util.log import *
from util.Res import Res


class SensorServer(object):

    def __init__(self):
        self.server_ip = "tcp://*:8005"
        self.endpoints = {}
        self.ser = None
        self._init_fliter()

    def _init_fliter(self):
        self._lig_N = 10
        self._lig_A = 100.0
        self._lig_S = self._lig_A*self._lig_N

    def _fliter_data(self, C):  # average fliter
        self._lig_S = self._lig_S - self._lig_A + C
        self._lig_A = self._lig_S / self._lig_N
        return int(self._lig_A)

    def _read_serial(self):
        try:
            self.ser = serial.Serial('/dev/tty.usbserial', 115200)
        except Exception, ex:
            ERROR(ex)
            return

        while True:
            info = self.ser.readline()[:-1]
            infos = info.split('#')
            if len(infos) == 5:
                sensor = {
                        'temp': infos[0],
                        'hum': infos[1],
                        'pir': infos[2],
                        'lig': self._fliter_data(float(infos[3])),
                        'addr': infos[4],
                        }
                INFO(sensor)
                self.endpoints[sensor['addr']] = sensor
            else:
                INFO(str(infos))

    def _handle_cmd(self, target, cmd):
        if cmd == 'list':
            return {'res': self.endpoints}

        if target not in self.endpoints:
            return {"res": "target not exist."}
        elif cmd == 'all':
            return {'res': self.endpoints[target]}
        else:
            if cmd not in self.endpoints[target]:
                return {"res": "cmd not exist."}
            else:
                return {'res': self.endpoints[target][cmd]}

    def _handle_req(self, req):
        try:
            json_req = json.loads(req)
            target = json_req["target"]
            cmd = json_req["cmd"]
            return json.dumps(self._handle_cmd(target, cmd))
        except Exception, ex:
            ERROR(ex)
            return json.dumps({"res": "error"})

    def start(self):
        INFO("start sensor server...")
        INFO("bind to" + self.server_ip)

        serial_t = threading.Thread(
                    target=self._read_serial,
                    )
        serial_t.daemon = True
        serial_t.start()

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
                    rep = self._handle_req(req)
                    self.socket.send_string(rep)
                    INFO("recv req:" + req)
            except (KeyboardInterrupt, SystemExit):
                if self.ser is not None:
                    self.ser.close()
                raise
            except:
                WARN("socket timeout.")
        self.socket.close()


if __name__ == '__main__':
    server = SensorServer()
    server.start()
