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



import argparse
import threading
import time
import json
import subprocess
import urllib, urllib2
import os
import base64
import errno
from datetime import datetime

import paho.mqtt.client as mqtt

from util.Res import Res
from util.log import *


class mqtt_server_proxy:
    
    NO_HEAD_FLAG = "*"
    BASE64_SUB_KEY = "/lehome/base64"
    MESSAGE_DIRECTORY = "./usr/message/"

    def __init__(self, address):
        if not address is None:
            INFO("connect to home: %s " % (address))
            self._home_address = address

            settings = Res.init("init.json")
            self._device_id = settings['id'].encode("utf-8")
            self._server_addr = settings['connection']['mqtt_server'].encode("utf-8")
            self._trigger_cmd = settings['command']['trigger'][0].encode("utf-8")
            self._finish_cmd = settings['command']['finish'][0].encode("utf-8")
            INFO("load device id:%s" % self._device_id)
        else:
            ERROR("address is empty")

    def _send_cmd_to_home(self, cmd):
        if not cmd is None and not cmd == "":
            DEBUG("send cmd %s to home." % (cmd, ))
            if cmd.startswith(mqtt_server_proxy.NO_HEAD_FLAG):
                cmd = cmd[1:]
            else:
                cmd = "%s%s%s" % (self._trigger_cmd, cmd, self._finish_cmd)

            try:
                data = {"cmd": cmd}
                enc_data = urllib.urlencode(data)
                response = urllib2.urlopen(self._home_address,
                                            enc_data,
                                            timeout=5).read()
            except urllib2.HTTPError, e:
                ERROR(e)
                return False
            except urllib2.URLError, e:
                ERROR(e)
                return False
            except Exception, e:
                ERROR(e)
                return False
            else:
                DEBUG("home response: " + response)
                return True
        else:
            ERROR("cmd is invaild.")
            return False

    def start(self):
        self._fetch_worker()
        # fetch_t = threading.Thread(
        #             target=self._fetch_worker
        #             )
        # fetch_t.daemon = True
        # fetch_t.start()
        # time.sleep(100)

    def _fetch_worker(self):
        INFO("start fetching cmds.")
        self._mqtt_client = mqtt.Client()
        self._mqtt_client.on_connect = self._on_mqtt_connect
        self._mqtt_client.on_message = self._on_mqtt_message 
        self._mqtt_client.connect(self._server_addr, 1883, 60)
        self._mqtt_client.loop_forever() 

    def _on_mqtt_connect(self, client, userdata, flags, rc):
        print("mqtt server connected with result code "+str(rc))
        subscribables = [
            (self._device_id, 1),
            (self._device_id + mqtt_server_proxy.BASE64_SUB_KEY, 1)
            ]
        client.subscribe(subscribables)

    def _on_mqtt_message(self, client, userdata, msg):
        payload = str(msg.payload)
        print(msg.topic + " " + payload) 
        if payload is not None and len(payload) != 0:
            if msg.topic == self._device_id:
                DEBUG("sending payload to home:%s" % payload)
                try:
                    self._send_cmd_to_home(payload)
                except Exception, ex:
                    import traceback
                    traceback.format_exc()
                    print "exception in _on_mqtt_message, normal topic:", ex
            elif msg.topic == self._device_id + mqtt_server_proxy.BASE64_SUB_KEY:
                try:
                    datas = json.loads(payload, strict=False)
                    self._handle_base64_payload(datas)
                except Exception, ex:
                    import traceback
                    traceback.format_exc()
                    print "exception in _on_mqtt_message, message topic", ex

    def _handle_base64_payload(self, datas):
        mtype = datas["type"]
        if mtype == "message":
            try:
                audio_data = base64.b64decode(datas["payload"])
                file_name = datas["filename"]
                if file_name is None or len(file_name) == 0:
                    ERROR("no filename for message base64 request")
                    return
                path = mqtt_server_proxy.MESSAGE_DIRECTORY
                try:
                    os.makedirs(path)
                except OSError as exc:
                    if exc.errno == errno.EEXIST and os.path.isdir(path):
                        pass
                    else:
                        ERROR(exc)
                        return

                filepath = path + datetime.now().strftime("%m-%d-%H-%M-%S") + ".spx"
                # filepath = path + file_name
                with open(filepath, "wb") as f:
                    f.write(audio_data)
                INFO("finish writing message file:%s, now send it to home." % filepath)

                self._send_cmd_to_home(u"显示#你有新留言#".encode("utf-8"))
                self._send_cmd_to_home(u"播放留言最新".encode("utf-8"))

            except Exception, ex:
                ERROR(ex)
                ERROR("decoding message error")
        else:
            print "unknown payload type in base64"

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
                    description='mqtt_server_proxy.py -a address')
    parser.add_argument('-a',
                        action="store",
                        dest="address",
                        default="http://localhost:8000/home/cmd",
                        )
    args = parser.parse_args()
    address = args.address

    INFO("mqtt server proxy is activate.")
    mqtt_server_proxy(address).start()
