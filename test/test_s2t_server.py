#!/usr/bin/env python
# encoding: utf-8


import sys
import argparse
import zmq
from util.log import *


parser = argparse.ArgumentParser(
                description='server.py -b <port>')
parser.add_argument('-p',
                    action="store",
                    dest="bind_to",
                    default="8000",
                    help="server port")
args = parser.parse_args()
bind_to = args.bind_to
INFO("bind to %s " % (bind_to, ))
context = zmq.Context()
sock = context.socket(zmq.PUB)
sock.bind("tcp://*:" + bind_to)

INFO('initlizing test...')

while True:
    cmd = raw_input("input command:").decode(sys.stdin.encoding)
    sock.send_string(cmd)
