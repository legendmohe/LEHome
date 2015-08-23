
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

from util.log import *
import vender.gpio

gpio = vender.gpio

class RemoteButtonController(object):
    def __init__(self):
        self.input_pin = ["gpio2", "gpio4", "gpio7", "gpio8"]
        self.mapping_btn = {"gpio2":"B", "gpio4":"C", "gpio7":"D", "gpio8":"A"}
        self.pin_state = {}
        self.setup()

    def delay(self, ms):
        # time.sleep(ms)
        time.sleep(1.0*ms/1000)

    def beep(self):
        subprocess.call(["sudo", "mplayer", "./usr/res/com_start.mp3"])

    def setup(self):
        for pin in self.input_pin:
            gpio.pinMode(pin, gpio.INPUT)
            self.pin_state[pin] = gpio.LOW

    def get(self):
        ret = []
        for pin in self.input_pin:
            state = gpio.digitalRead(pin)
            if not self.pin_state[pin] == state:
                self.pin_state[pin] = state
                # print "btn press!", self.mapping_btn[pin], state
                if state == gpio.HIGH:
                    ret.append(self.mapping_btn[pin])
        # self.delay(10)
        if len(ret) == 0:
            return None
        return ret

    # def activate(self):
    #     self.loop()

class quick_button(object):

    def __init__(self):
        self._event_queue = Queue()
        self._configure(conf_path="./usr/btn_conf.json")
        self._init_params()
        self._btn_ctler = RemoteButtonController()

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

    def _fetch_event(self):
        # time.sleep(random.uniform(0.0, 1.5))
        # return "1"
        return self._btn_ctler.get()

    def _is_event_vaild(self, event):
        if event is None:
            return False
        return True

    def _event_produce_worker(self):
        while True :
            try:
                event = self._fetch_event()
                if not self._is_event_vaild(event):
                    # WARN("invaild event.")
                    continue
                print "event", event
                INFO("quick_btn got event:%s" % event)
                self._event_queue.put(event)
                self._btn_ctler.delay(10)
            except (KeyboardInterrupt, SystemExit):
                self.stop()
                raise
            except Exception, ex:
                ERROR(ex)
                time.sleep(1)

    def _event_consume_worker(self):
        cmd_buf = []
        while True:
            try:
                event = self._event_queue.get(timeout=self._timeout)
                self._event_queue.task_done()
                cmd_buf.extend(event)
            except Empty:
                if len(cmd_buf) > 0:
                    print "timeout:", cmd_buf
                    # self.beep()
                    DEBUG('dequeue event timeout. now collecting buffer.')
                    self._map_buffer_to_command(cmd_buf)
                del cmd_buf[:]
            except (KeyboardInterrupt, SystemExit):
                self.stop()
                raise
            except Exception, ex:
                ERROR(ex)
                time.sleep(1)

    def _map_buffer_to_command(self, cmd_buf):
        cmds = self._conf["command"]
        cmd = "".join(cmd_buf)
        if cmd in cmds:
            self._send_cmd_to_home(cmds[cmd].encode("utf-8"))

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

        produce_t = threading.Thread(
                    target=self._event_produce_worker
                    )
        produce_t.daemon = True
        produce_t.start()

        # consume_t = threading.Thread(
        #             target=self._event_consume_worker
        #             )
        # consume_t.daemon = True
        # consume_t.start()
        self._event_consume_worker()

    def stop(self):
        INFO("quick_button stop.")

if __name__ == '__main__':
    quick_button().start()
