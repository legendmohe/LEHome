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
import random
import time
import subprocess
import json
from Queue import Queue, Empty
import collections
import urllib, urllib2

import pygame

from util.log import *
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BOARD)

class RemoteButtonController(object):
    def __init__(self, state_queue):
        self.input_pin = [13, 15, 16, 18]
        self.mapping_btn = {13:"C", 15:"B", 16:"A", 18:"D"}
        self._state_queue = state_queue
        self.setup()

    def delay(self, ms):
        time.sleep(1.0*ms/1000)

    def beep(self):
        if self._beep is not None:
            self._beep.play()

    def setup(self):
        for pin in self.input_pin:
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            GPIO.add_event_detect(
                                pin,
                                GPIO.RISING,
                                callback=self._interupt,
                                bouncetime=50
            )

        pygame.init()
        try:
            self._beep = pygame.mixer.Sound("./usr/res/com_btn2.wav")
        except Exception, ex:
            print "quick button beep init error!"
            ERROR("quick button beep init error!")
            self._beep = None

    def _interupt(self, pin):
        if self._state_queue is not None:
            if pin in self.mapping_btn:
                INFO("interrupt: %s" % self.mapping_btn[pin])
                self.beep()
                self._state_queue.put(self.mapping_btn[pin])

    def cleanup(self):
        GPIO.setmode(GPIO.BOARD)
        for pin in self.input_pin:
            GPIO.remove_event_detect(pin)
        # GPIO.cleanup()

class quick_button(object):

    def __init__(self):
        self._event_queue = Queue()
        self._configure(conf_path="./usr/btn_conf.json")
        self._init_params()
        self._btn_ctler = RemoteButtonController(self._event_queue)

    def _configure(self, conf_path):
        with open(conf_path) as f:
            conf_json = json.load(f)
            if not conf_json:
                ERROR("error: invaild btn_conf.json")
                return
        self._conf = conf_json

    def _init_params(self):
        self.server_ip = self._conf["server_ip"]
        self._timeout = self._conf["timeout"]
        self._trigger_cmd = self._conf['trigger'].encode("utf-8")
        self._finish_cmd = self._conf['finish'].encode("utf-8")
        self._reset_cmd = self._conf['reset']
        self._cmds = {}
        self._direct_key = {}
        for key in self._conf["command"]:
            value = self._conf["command"][key]
            if key.endswith("*"):
                key = key[:-1]
                self._direct_key[key] = value
                # print key, value
            else:
                self._cmds[key] = value

    def reload_cmds(self):
        self._configure(conf_path="./usr/btn_conf.json")
        self._init_params()

    def _is_event_vaild(self, event):
        if event is None:
            return False
        return True

    def _is_reset_cmd(self, cmd):
        return cmd == self._reset_cmd

    def _event_consume_worker(self):
        cmd_buf = []
        while True:
            try:
                event = self._event_queue.get(timeout=self._timeout)
                print "got event: ", event
                self._event_queue.task_done()
                if len(cmd_buf) == 0 and event in self._direct_key:
                    self._map_buffer_to_command(event)
                else:
                    cmd_buf.extend(event)
            except Empty:
                if len(cmd_buf) > 0:
                    print "timeout:", cmd_buf
                    DEBUG('dequeue event timeout. now collecting buffer.')
                    cmd = "".join(cmd_buf)
                    if self._is_reset_cmd(cmd):
                        INFO("reload cmds.")
                        self.reload_cmds()
                    else:
                        self._map_buffer_to_command(cmd)
                del cmd_buf[:]
            except (KeyboardInterrupt, SystemExit):
                self.stop()
                raise
            except Exception, ex:
                ERROR(ex)
                time.sleep(1)

    def _map_buffer_to_command(self, cmd):
        if cmd in self._direct_key:
            self._send_cmd_to_home(self._direct_key[cmd].encode("utf-8"))
        elif cmd in self._cmds:
            self._send_cmd_to_home(self._cmds[cmd].encode("utf-8"))

    def _send_cmd_to_home(self, cmd):
        print "find mapping! send to home:", cmd
        # pass
        if not cmd is None and not cmd == "":
            INFO("send cmd %s to home." % (cmd, ))
            cmd = "%s%s%s" % (self._trigger_cmd, cmd, self._finish_cmd)

            try:
                data = {"cmd": cmd}
                enc_data = urllib.urlencode(data)
                response = urllib2.urlopen(self.server_ip,
                                            enc_data,
                                            timeout=5).read()
            except urllib2.HTTPError, e:
                ERROR(e)
                return False
            except urllib2.URLError, e:
                ERROR(e)
                return False
            else:
                INFO("home response: " + response)
                return True
        else:
            ERROR("cmd is invaild.")
            return False

    def start(self):
        INFO("start quick_button server...")
        INFO("command server ip:" + self.server_ip)

        self._event_consume_worker()

    def stop(self):
        INFO("quick_button stop.")
        self._btn_ctler.cleanup()

if __name__ == '__main__':
    qb = quick_button()
    try:
        qb.start()
    finally:
        qb.stop()
        INFO("clean GPIO. now exit")
    print "exit."
