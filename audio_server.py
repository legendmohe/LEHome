#!/usr/bin/env python
# encoding: utf-8


import sys
import signal
import argparse
import tornado.ioloop
import tornado.web
from lib.speech.Speech import Text2Speech
from util.log import *


#--- http://stackoverflow.com/questions/17101502/how-to-stop-the-tornado-web-server-with-ctrlc

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

#----

class stopHandler(tornado.web.RequestHandler):
    def get(self, url):
        self.write("True")


class playHandler(tornado.web.RequestHandler):
    def get(self, url):
        self.write("True")


class pauseHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("True")


class resumeHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("True")


application = tornado.web.Application([
    (r"/play/(.*)", playHandler),
    (r"/stop/(.*)", stopHandler),
    (r"/resume", resumeHandler),
    (r"/pause", pauseHandler),
])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
                    description='audio_server.py -p port')
    parser.add_argument('-p',
                        action="store",
                        dest="port",
                        default="8001",
                        )
    args = parser.parse_args()

    INFO("initlizing...")
    port = args.port
    INFO("bind to %s " % (port))
    signal.signal(signal.SIGINT, signal_handler)
    application.listen(port)
    tornado.ioloop.PeriodicCallback(try_exit, 100).start()
    tornado.ioloop.IOLoop.instance().start()
