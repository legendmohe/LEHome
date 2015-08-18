#!/usr/bin/env python
# encoding: utf-8
# Copyright 2014 Xinyu, He <legendmohe@foxmail.com>
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
import json
import time
import socket
from util.thread import TimerThread
from util.Res import Res
from util.log import *


class SwitchHelper:

    HEARTBEAT_RATE = 3
    SOCKET_TIMEOUT = 5
    RETRY_TIME = 3
    SCAN_PORT = 48899
    SWITCH_PORT = 8899
    BOARDCAST_ADDRESS = "255.255.255.255"

    def __init__(self):
        init_json = Res.init("init.json")
        self.scan_ip = SwitchHelper.BOARDCAST_ADDRESS
        self.name2ip = init_json["switchs"]

        self._send_lock = threading.Lock()
        self.switchs = {}
        self._init_heartbeat()

    def _init_heartbeat(self):
        self._init_heartbeat_socket()
        self._send_hb_thread = threading.Thread(target=self._heartbeat_recv)
        self._send_hb_thread.daemon = True
        self._send_hb_thread.start()

        self._heartbeat_thread = TimerThread(
                                    interval=SwitchHelper.HEARTBEAT_RATE,
                                    target=self._heartbeat_send
                                    )
        self._heartbeat_thread.start()

    def _init_heartbeat_socket(self):
        self._hb_sock = self._get_udp_socket()
        bind_address = ('0.0.0.0', SwitchHelper.SCAN_PORT)
        self._hb_sock.bind(bind_address)
        self._hb_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, True)
        self._hb_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
        # self._hb_sock.settimeout(SwitchHelper.HEARTBEAT_RATE/2)

    def ip_for_name(self, name):
        return self.name2ip.get(name, None)

    def name_for_ip(self, ip):
        for name in self.name2ip:
            if self.name2ip[name] == ip:
                return name
        return None

    def send_open(self, target_ip):
        if not target_ip in self.switchs:
            ERROR("target_ip not exist: " + target_ip)
            return
        cmd = self._get_switch_cmd("ON")
        res = self._send_cmd(target_ip, cmd)
        INFO("send_open:%s" % res)
        if res == "+OK" or res == "+ok":
            self.switchs[target_ip]['status'] = "on"
        return res

    def send_close(self, target_ip):
        if not target_ip in self.switchs:
            ERROR("target_ip not exist: " + target_ip)
            return
        cmd = self._get_switch_cmd("OFF")
        res = self._send_cmd(target_ip, cmd)
        INFO("send_close:%s" % res)
        if res == "+OK" or res == "+ok":
            self.switchs[target_ip]['status'] = "off"
        return res

    def show_state(self, target_ip):
        if not target_ip in self.switchs:
            ERROR("target_ip not exist: " + target_ip)
            return None
        return self.switchs[target_ip]["status"]

    def show_info(self, target_ip):
        if not target_ip in self.switchs:
            ERROR("target_ip not exist: " + target_ip)
            return
        cmd = self._get_info_cmd()
        recv = self._send_cmd(target_ip, cmd)
        if recv is None or len(recv) == 0:
            return None
        info = recv[5:-1].split(",")
        return  {
                "I": info[0] if len(info[0]) != 0 else "0",
                "U": info[1] if len(info[1]) != 0 else "0",
                "F": info[2] if len(info[2]) != 0 else "0",
                "P": info[3] if len(info[3]) != 0 else "0",
                "PQ": info[4] if len(info[4]) != 0 else "0",
                "E": info[5] if len(info[5]) != 0 else "0",
                "EQ": info[6] if len(info[6]) != 0 else "0",
                }

    def readable_info(self, info):
        if info is None or len(info) == 0:
            return ""
        I = "%.2f" % (float(info["I"])/100.0) + "A"
        U = "%.2f" % (float(info["U"])/100.0) + "V"
        F = "%.2f" % (float(info["F"])/100.0) + "Hz"
        P = "%.2f" % (float(info["P"])/10.0) + "W"
        PQ = info["P"] + "W"
        E = info["E"] + "WH"
        EQ = info["EQ"] + "WH"
        return "".join([
                u"功率:%s " % P,
                u"电流:%s " % I,
                u"电压:%s " % U,
                # u"频率:%s " % F,
                # u"有功功率:%s " % P,
                # u"无功功率:%s " % PQ,
                # u"有功能量值:%s " % E,
                # u"无功能量值:%s" % EQ,
                ])

    def _format_time(self):
        return time.strftime("%Y%m%d%H%M%S", time.localtime())

    def _get_udp_socket(self):
        return socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def _get_cmd_socket(self):
        return socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def _get_switch_cmd(self, action):
        return "AT+YZSWITCH=1,%s,%s\r\n" % (action, self._format_time())

    def _get_info_cmd(self):
        return "AT+YZOUT\r\n"

    def _get_heartbeat_cmd(self):
        return 'YZ-RECOSCAN'

    def _send_cmd(self, target_ip, cmd):
        if target_ip is None or len(target_ip) == 0:
            ERROR("invaild target_ip.")
            return
        if cmd is None or len(cmd) == 0:
            ERROR("invaild switch cmd.")
            return

        with self._send_lock:
            # sock = self._get_cmd_socket()
            # sock.connect()
            INFO("Switch send command:%s to:%s" % (cmd, target_ip))
            for i in range(0, SwitchHelper.RETRY_TIME):
                try:
                    sock = socket.create_connection(
                            (target_ip, SwitchHelper.SWITCH_PORT),
                            SwitchHelper.SOCKET_TIMEOUT)
                    time.sleep(0.5)
                    sock.send(cmd)
                    recv = sock.recv(512)
                    sock.close()
                    return recv.strip()
                except socket.timeout:
                    ERROR("SwitchHelper cmd socket timeout.")
                except Exception, ex:
                    ERROR(ex)
            return None

    def _heartbeat_send(self):
        # for ip in self.switchs:
        #     self.switchs[ip]["status"] = "-1"

        sock = self._hb_sock
        address = (self.scan_ip, SwitchHelper.SCAN_PORT)
        sock.sendto(self._get_heartbeat_cmd(), address)
        DEBUG("send switch heartbeat to:%s" % (address, ))

    def _heartbeat_recv(self):
        sock = self._hb_sock
        while True:
            try:
                recv, address = sock.recvfrom(512)
                DEBUG("recv switch heartbeat:%s from:%s" % (recv, address))
                status = recv.strip().split(',')
                if len(status) < 5:
                    continue

                switch = {}
                switch["ip"] = status[0]
                switch["mac"] = status[1]
                switch["name"] = self.name_for_ip(status[0])
                switch["status"] = "on" if status[4] == "1" else "off"
                self.switchs[switch["ip"]] = switch

            except socket.timeout:
                WARN("heartbeat timeout. ")

