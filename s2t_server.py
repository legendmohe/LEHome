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
from util.log import *
from lib.speech.Speech import Speech2Text
import zmq


parser = argparse.ArgumentParser(
                description='server.py -b <port>')
parser.add_argument('-p',
                    action="store",
                    dest="bind_to",
                    default="8000",
                    help="server port")
args = parser.parse_args()
bind_to = args.bind_to
INFO("host:%s " % (bind_to, ))
context = zmq.Context()
sock = context.socket(zmq.PUB)
sock.bind("tcp://*:" + bind_to)

def speech_callback(result, confidence):
    global sock
    threshold = 0.5

    INFO("result: " + result + " | " + str(confidence))
    if confidence > threshold:
        sock.send_string(result)


INFO('initlizing recognize...')
Speech2Text.collect_noise()
reg = Speech2Text(speech_callback)

if not reg:
    CRITICAL("recognizer init faild.")
    sys.exit(1)
else:
    reg.start_recognizing()

while True:
    time.sleep(10)
