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

    SERIAL_ADDR = '/dev/ttyUSB0'

    def __init__(self):
        self.server_ip = "tcp://*:8005"
        self.endpoints = {}
        self.ser = None
        self._init_fliter()

    def _init_fliter(self):
        self.fliter = {}
        N = [5, 5, 5, 1]
        A = [100.0, 40.0, 90.0, 1.0]
        for index, sensor_type in enumerate(['lig', 'temp', 'hum', 'pir']):
            self.fliter[sensor_type] = {}
            self.fliter[sensor_type]['N'] = N[index]
            self.fliter[sensor_type]['A'] = A[index]
            self.fliter[sensor_type]['S'] = \
                    self.fliter[sensor_type]['N']*self.fliter[sensor_type]['A']

    def _fliter_data(self, sensor_type, C):  # average fliter
        if sensor_type not in self.fliter:
            return -1
        sensor_fliter = self.fliter[sensor_type]
        if sensor_fliter is None:
            return -1
        sensor_fliter['S'] = sensor_fliter['S'] - sensor_fliter['A'] + C
        sensor_fliter['A'] = sensor_fliter['S']/sensor_fliter['N']
        return sensor_fliter['A']

    def _read_serial(self):
        try:
            self.ser = serial.Serial(SensorServer.SERIAL_ADDR, 115200)
        except Exception, ex:
            ERROR(ex)
            return

        while True:
            info = self.ser.readline()[:-1]
            infos = info.split('#')
            if len(infos) == 5:
                temp = float('%.2f'% self._fliter_data('temp', float(infos[0])))
                hum = float('%.2f'% self._fliter_data('hum', float(infos[1])))
                pir = float('%.0f'% self._fliter_data('pir', float(infos[2])))
                lig = float('%.2f'% self._fliter_data('lig', float(infos[3])))
                sensor = {
                        'temp': temp,
                        'hum': hum,
                        'pir': int(pir),
                        'lig': lig,
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
