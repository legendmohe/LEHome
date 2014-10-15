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


import sys
import argparse
import time
import threading
import zmq
from util.log import *
from lib.speech.Speech import Speech2Text


parser = argparse.ArgumentParser(
                            description='server.py -t <address>')
parser.add_argument('-t',
                    action="store",
                    dest="send_to",
                    default="192.168.1.101:8000",
                    help="server address")
args = parser.parse_args()
send_to = args.send_to
INFO("host:%s " % (send_to, ))
context = zmq.Context()
sock = context.socket(zmq.REQ)
sock.connect("tcp://" + send_to)

callbacl_lock = threading.Lock()
def speech_callback(result, confidence):
    global sock, callbacl_lock
    with callbacl_lock:
        threshold = 0.5
        INFO("result: " + result + " | " + str(confidence))
        if confidence > threshold:
            sock.send_string(result)
            message = sock.recv()
            print("Received reply %s [%s]" % (result, message))


INFO('initlizing recognize...')
# Speech2Text.collect_noise()
reg = Speech2Text(speech_callback)

if not reg:
    CRITICAL("recognizer init faild.")
    sys.exit(1)
else:
    reg.start_recognizing()

while True:
    time.sleep(10)
