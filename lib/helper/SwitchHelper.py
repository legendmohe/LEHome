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


class SwitchHelper:

    def __init__(self):
        init_json = Res.init("init.json")
        self.server_ip = init_json["connection"]["switch_server"]
        self.name2ip = init_json["switchs"]

        self._send_lock = threading.Lock()
        context = zmq.Context()
        self.socket = context.socket(zmq.REQ)
        self.socket.setsockopt(zmq.LINGER, 0)
        self.socket.connect(self.server_ip)
        time.sleep(0.5)
        self.init_switchs()

    def init_switchs(self):
        self.switchs = self.list_state()
        if self.switchs is None:
            self.switchs = []

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
        self.list_state()
        cmd = self.get_vaild_cmd(target_ip, "open")
        rep = self.send_cmd(cmd)
        try:
            rep = json.loads(rep)["res"]
        except:
            ERROR("error: invaild switch response")
            return
        self.show_state(target_ip)
        return rep

    def send_close(self, target_ip):
        self.list_state()
        cmd = self.get_vaild_cmd(target_ip, "close")
        rep = self.send_cmd(cmd)
        try:
            rep = json.loads(rep)["res"]
        except:
            ERROR("error: invaild switch response")
            return
        self.show_state(target_ip)
        return rep

    def send_cmd(self, cmd):
        if cmd is None or len(cmd) == 0:
            ERROR("invaild switch cmd.")
            return
        INFO("sending cmd to switch server:" + cmd)

        self._send_lock.acquire()
        message = ""
        # try:
        #     url = self.server_ip + '?'
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
            if poller.poll(30*1000):
                message = self.socket.recv_string()
                INFO("recv msgs:" + message)
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
        #     ERROR("can't connect to switch server.")
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
        return state

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
        self.switchs = res
        return self.switchs
