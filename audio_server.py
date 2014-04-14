#!/usr/bin/env python
# encoding: utf-8


import sys
import threading
import signal
from Queue import Queue
import argparse
import tornado.ioloop
import tornado.web
from lib.speech.Speech import Text2Speech
from util.log import *
from vender.mplayer import MPlayer


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

MPlayer.populate()
mp_context = {}
mp_queue = Queue()

application = tornado.web.Application([
    (r"/play/([^/]+)", PlayHandler),
    (r"/clean", CleanQeueuHandler),
    (r"/stop/([^/]+)", StopHandler),
    (r"/resume", ResumeHandler),
    (r"/pause", PauseHandler),
])


class RETURNCODE:
    SUCCESS = 1
    ERROR   = 2
    FAIL    = 3
    EMPTY   = 4
    NO_RES  = 5


class StopHandler(tornado.web.RequestHandler):
    def get(self, url):
        global mp_context
        if not url in mp_context:
            WARN("%s is not playing" % (url, ))
            self.write(RETURNCODE.FAIL)
        else:
            mp = mp_context[url]
            mp.stop()
            self.write(RETURNCODE.SUCCESS)


class CleanQeueuHandler(tornado.web.RequestHandler):
    def get(self):
        global mp_context
        global mp_queue

        with mp_queue.mutex:
            mp_queue.queue.clear()
        mp = mp_context["queue"]
        mp.stop()

        self.write(RETURNCODE.SUCCESS)


class PlayHandler(tornado.web.RequestHandler):
    def get(self, url):
        if url is None or url == "":
            INFO("url is empty")
            self.write(str(RETURNCODE.EMPTY))
            return
        INFO("%s is playing." % (url,))
        self.write(str(RETURNCODE.SUCCESS))
        is_inqueue = self.get_argument("inqueue", None)
        if is_inqueue is None:
            play_audio(url)
        else:
            play_audio_inqueue(url)


class PauseHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("True")


class ResumeHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("True")


def play_audio(url):
    global mp_context
    if url in mp_context:
        INFO("%s is already playing" % (url, ))
        return

    def worker(url):
        mp = MPlayer()
        mp_context[url] = mp
        mp.loadfile(url)
        del mp_context[url]
    t = threading.Thread(target=worker)
    t.setDaemon(True)
    t.start()


def play_audio_inqueue(url):
    global mp_queue
    mp_queue.put(url)


def queue_worker():
    global mp_context
    global mp_queue

    mp = mp_context["queue"]
    while True:
        url = mp_queue.get()
        mp.loadfile(url)
        mp_queue.task_done()


def init_player():
    mp_context["queue"] = MPlayer()
    t = threading.Thread(target=queue_worker)
    t.setDaemon(True)
    t.start()


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

    init_player()

    tornado.ioloop.PeriodicCallback(try_exit, 100).start()
    tornado.ioloop.IOLoop.instance().start()
