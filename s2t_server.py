#!/usr/bin/env python
# encoding: utf-8


import sys
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
