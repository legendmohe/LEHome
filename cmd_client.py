#!/usr/bin/env python
# encoding: utf-8


import sys
from util.log import *
from lib.speech.Speech import Speech2Text
import zmq


if len (sys.argv) < 2:
    print 'usage: server <bind-to>'
    sys.exit (1)

bind_to = sys.argv[1]
INFO("host:%s " % (bind_to, ))
context = zmq.Context()
sock = context.socket(zmq.PUB)
sock.bind(bind_to)

def speech_callback(result, confidence):
    global sock
    threshold = 0.5

    INFO("result: " + result + " | " + str(confidence))
    if confidence > threshold:
        sock.send(result)


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
