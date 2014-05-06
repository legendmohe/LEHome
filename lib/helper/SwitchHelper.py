#!/usr/bin/env python
# encoding: utf-8

import zmq
from util.Res import Res
from util.log import *


class SwitchHelper:

    def __init__(self):
        init_json = Res.init("init.json")
        self.server_ip = init_json["connection"]["switch_server"]
        self.name2ip = init_json["switchs"]

        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.REQ)
        self.socket.connect(self.server_ip)
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
        if not target_ip in self.switchs:
            return None
        return cmd + "|" + target_ip

    def send_open(self, target_ip):
        cmd = self.get_vaild_cmd(target_ip, "open")
        rep = self.send_cmd(cmd)
        self.list_state()
        return rep

    def send_close(self, target_ip):
        cmd = self.get_vaild_cmd(target_ip, "close")
        rep = self.send_cmd(cmd)
        self.list_state()
        return rep

    def send_cmd(self, cmd):
        if cmd is None or len(cmd) == 0:
            ERROR("invaild switch cmd.")
            return
        INFO("sending cmd to switch server:" + cmd)
        self.socket.send_string(cmd)
        message = self.socket.recv_string()
        INFO("recv msgs:" + message)
        return message

    def show_state(self, target_ip):
        cmd = self.get_vaild_cmd(target_ip, "check")
        state = self.send_cmd(cmd)
        self.switchs[target_ip]["state"] = state
        return state

    def list_state(self):
        res = {}
        switchs = self.send_cmd("list")
        if not switchs is None and len(switchs) > 0:
            for switch_state in switchs.split("\n"):
                states = switch_state.split("|")
                res[states[0]] = {}
                res[states[0]]["name"] = self.name_for_ip(states[0])
                res[states[0]]["mac"] = states[1]
                res[states[0]]["state"] = states[2]
        return res
