#!/usr/bin/env python
# encoding: utf-8

import threading
import json
import time
# import urllib
# import urllib2
import zmq
from util.Res import Res
from util.log import *


class SensorHelper:

    def __init__(self):
        init_json = Res.init("init.json")
        self.server_ip = init_json["connection"]["sensor_server"]
        self.name2addr = init_json["sensors"]

        self._send_lock = threading.Lock()
        context = zmq.Context()
        self.socket = context.socket(zmq.REQ)
        self.socket.setsockopt(zmq.LINGER, 0)
        self.socket.connect(self.server_ip)
        time.sleep(0.5)
        self.init_sensors()

    def init_sensors(self):
        self.sensors = self.list_state()
        if self.sensors is None:
            self.sensors = []

    def addr_for_name(self, name):
        return self.name2addr.get(name, None)

    def name_for_addr(self, addr):
        for name in self.name2addr:
            if self.name2addr[name] == addr:
                return name
        return None

    def get_vaild_cmd(self, target_addr, cmd):
        if target_addr and not target_addr in self.sensors:
            return None
        vaild_cmd = json.dumps({"cmd": cmd, "target": target_addr})
        return vaild_cmd

    def get_temp(self, target_addr):
        return self.get_sensor_value(target_addr, "temp")

    def get_humidity(self, target_addr):
        return self.get_sensor_value(target_addr, "hum")

    def get_pir(self, target_addr):
        return self.get_sensor_value(target_addr, "pir")

    def get_lig(self, target_addr):
        lig = self.get_sensor_value(target_addr, "lig")
        if lig is not None:
            lig = str(int(lig))
        return lig

    def get_sensor_value(self, target_addr, sensor_type):
        self.list_state()
        cmd = self.get_vaild_cmd(target_addr, sensor_type)
        rep = self.send_cmd(cmd)
        try:
            rep = json.loads(rep)["res"]
        except:
            ERROR("error: invaild sensor response")
            return
        return rep

    def send_cmd(self, cmd):
        if cmd is None or len(cmd) == 0:
            ERROR("invaild sensor cmd.")
            return
        DEBUG("sending cmd to sensor server:" + cmd)

        self._send_lock.acquire()
        message = ""
        # try:
        #     url = self.server_addr + '?'
        #     url += urllib.urlencode({"json": cmd.encode("utf-8")})
        #     message = urllib2.urlopen(url, timeout=30).read()
        #     INFO("recv msgs:" + message)
        # except Exception, ex:
        #     ERROR(ex)
        #     WARN("request timeout.")
        # ----------------------------
        self.socket.send_string(cmd)
        try:
            poller = zmq.Poller()
            poller.register(self.socket, zmq.POLLIN)
            if poller.poll(5*1000):
                message = self.socket.recv_string()
                DEBUG("recv msgs:" + message)
        except:
            WARN("socket timeout.")
        # --------------
        # import pdb
        # pdb.set_trace()
        # import socket
        # try:
        #     s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #     s.connect(('192.168.1.239', 8004))
        #     s.send(cmd + '\n')
        #     message = s.recv(2048)
        #     INFO("recv msgs:" + message)
        #     s.close()
        # except Exception, ex:
        #     ERROR(ex)
        #     ERROR("can't connect to sensor server.")
        self._send_lock.release()
        return message

    def list_state(self):
        try:
            cmd = self.get_vaild_cmd("", "list")
            response = self.send_cmd(cmd)
            sensors = json.loads(response)["res"]
        except Exception, e:
            ERROR("error: " + str(e))
            return
        self.sensors = sensors
        return self.sensors

    def get_sensor_state(self, target_addr):
        if target_addr and not target_addr in self.sensors:
            return None
        self.list_state()
        return self.sensors[target_addr]
    
    def readable_state(self, state):
        try:
            res = u"温度:%s℃, 湿度:%s%%, 是否有人:%s, 光照:%d" \
                      % (
                         state['temp'],
                         state['hum'],
                         (u'是' if state['pir'] == u'0' else u'否'),
                         int(state['lig'])
                        )
            return res
        except Exception, ex:
            ERROR(ex)
            return ""
