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



import signal
import argparse
import zmq
import tornado.ioloop
import tornado.web
from util.Res import Res
from util.log import *


# http://stackoverflow.com/questions/17101502/how-to-stop-the-tornado-web-server-with-ctrlc
is_closing = False


def signal_handler(signum, frame):
    global is_closing
    logging.info('exiting...')
    is_closing = True


def try_exit():
    global is_closing
    if is_closing:
        # clean up here
        tornado.ioloop.IOLoop.instance().stop()
        logging.info('exit success')

# proxy


def initialize(address):
    global SOCK, POLLER
    if not address is None:
        INFO("connect to server: %s " % (address))
        context = zmq.Context()
        _sock = context.socket(zmq.REQ)
        _sock.setsockopt(zmq.LINGER, 0)
        poller = zmq.Poller()
        poller.register(_sock, zmq.POLLIN)
        _sock.connect(address)
        SOCK = _sock
        POLLER = poller
    else:
        ERROR("address is empty")


class CmdHandler(tornado.web.RequestHandler):

    def get(self, cmd):
        global SOCK, POLLER
        if not cmd is None and not cmd == "":
            INFO("send cmd %s to home." % (cmd, ))
            SOCK.send_string(cmd)
            if POLLER.poll(10*1000): # 10s timeout in milliseconds
                rep = SOCK.recv_string()
                self.write(rep)
            else:
                self.write("error")
        else:
            self.write("error")


class CmdListHandler(tornado.web.RequestHandler):

    def get(self):
        cmds = Res.init("init.json")["command"]
        for key in cmds:
            self.write("%s: " % (key, ))
            for cmd in cmds[key]:
                self.write("%s, " % (cmd, ))
            self.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
                    description='cmd_http_server.py -a address -b http_server_port')
    parser.add_argument('-a',
                        action="store",
                        dest="address",
                        default="tcp://localhost:8000",
                        )
    parser.add_argument('-b',
                        action="store",
                        dest="http_port",
                        default="8002",
                        )
    args = parser.parse_args()
    address = args.address
    http_port = args.http_port
    signal.signal(signal.SIGINT, signal_handler)

    INFO("http command server is activate.")
    initialize(address)
    application = tornado.web.Application([
                (r"/cmd/([^/]*)", CmdHandler),
                (r"/cmdlist", CmdListHandler),
                ])
    application.listen(http_port)
    INFO("listening to %s " % (http_port))
    tornado.ioloop.PeriodicCallback(try_exit, 100).start()
    tornado.ioloop.IOLoop.instance().start()
