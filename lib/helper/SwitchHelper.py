#!/usr/bin/env python
# encoding: utf-8

import threading
import json
import zmq
from util.Res import Res
from util.log import *


class SwitchHelper:

    def __init__(self):
        init_json = Res.init("init.json")
        self.server_ip = init_json["connection"]["switch_server"]
        self.name2ip = init_json["switchs"]

        self._send_lock = threading.Lock()
        self.init_switchs()

    def init_switchs(self):
        self.switchs = self.list_state()

    def ip_for_name(self, name):
        return self.name2ip.get(name, None)

    def name_for_ip(self, ip):
        for name in self.name2ip:
            if self.name2ip[name] == ip:
                return name
        return None

    def get_vaild_cmd(self, target_ip, cmd):
        if target_ip and not target_ip in self.switchs:
            return None
        vaild_cmd = json.dumps({"cmd": cmd, "target": target_ip})
        return vaild_cmd

    def send_open(self, target_ip):
        cmd = self.get_vaild_cmd(target_ip, "open")
        rep = self.send_cmd(cmd)
        try:
            rep = json.loads(rep)["res"]
        except:
            ERROR("error: invaild switch response")
            return
        self.list_state()
        return rep

    def send_close(self, target_ip):
        cmd = self.get_vaild_cmd(target_ip, "close")
        rep = self.send_cmd(cmd)
        try:
            rep = json.loads(rep)["res"]
        except:
            ERROR("error: invaild switch response")
            return
        self.list_state()
        return rep

    def send_cmd(self, cmd):
        if cmd is None or len(cmd) == 0:
            ERROR("invaild switch cmd.")
            return
        INFO("sending cmd to switch server:" + cmd)

        self._send_lock.acquire()
        message = ""
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.LINGER, 0)
        socket.connect(self.server_ip)
        socket.send_string(cmd)
        try:
            poller = zmq.Poller()
            poller.register(socket, zmq.POLLIN)
            if poller.poll(10*1000):
                message = socket.recv_string()
                INFO("recv msgs:" + message)
        except:
            WARN("socket timeout.")
        socket.close()
        context.term()
        self._send_lock.release()
        return message

    def show_state(self, target_ip):
        if not target_ip in self.switchs:
            ERROR("target_ip not exist: " + target_ip)
            return
        cmd = self.get_vaild_cmd(target_ip, "check")
        try:
            state = json.loads(self.send_cmd(cmd))["res"]
        except:
            ERROR("error: invaild switch response")
            return
        self.switchs[target_ip]["state"] = state
        return state.state

    def list_state(self):
        res = {}
        try:
            cmd = self.get_vaild_cmd("", "list")
            response = self.send_cmd(cmd)
            switchs = json.loads(response)["res"]["switchs"]
        except Exception, e:
            ERROR("error: " + str(e))
            return
        for switch in switchs:
            ip = switch["ip"]
            res[ip] = {}
            res[ip]["name"] = self.name_for_ip(ip)
            res[ip]["mac"] = switch["mac"]
            res[ip]["state"] = switch["state"]
        return res
