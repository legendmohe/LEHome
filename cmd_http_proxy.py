#!/usr/bin/env python
# encoding: utf-8


import signal
import argparse
import zmq
import tornado.ioloop
import tornado.web
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


def initialize(port):
    global SOCK
    if not port is None:
        INFO("bind to %s " % (port))
        context = zmq.Context()
        _sock = context.socket(zmq.PUB)
        _sock.bind("tcp://*:" + port)
        SOCK = _sock
    else:
        ERROR("port is empty")


class CmdHandler(tornado.web.RequestHandler):

    def get(self, cmd):
        global SOCK
        if not cmd is None and not cmd == "":
            INFO("send cmd %s to home." % (cmd, ))
            SOCK.send_string(cmd)
            self.write("cmd: %s" % (cmd, ))
        else:
            self.write("error")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
                    description='cmd_http_server.py -p port -b http_server_port')
    parser.add_argument('-p',
                        action="store",
                        dest="port",
                        default="7999",
                        )
    parser.add_argument('-b',
                        action="store",
                        dest="http_port",
                        default="8002",
                        )
    args = parser.parse_args()
    port = args.port
    http_port = args.http_port
    signal.signal(signal.SIGINT, signal_handler)

    INFO("http command server is activate.")
    initialize(port)
    application = tornado.web.Application([
                (r"/cmd/([^/]*)", CmdHandler)
                ])
    application.listen(http_port)
    tornado.ioloop.PeriodicCallback(try_exit, 100).start()
    tornado.ioloop.IOLoop.instance().start()
