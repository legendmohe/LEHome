#!/usr/bin/env python
# encoding: utf-8


import threading
import signal
from Queue import Queue
from time import sleep
import argparse
import tornado.ioloop
import tornado.web
from util.log import *
from mplayer import Player


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


# handlers


class RETURNCODE:
    SUCCESS = 1
    ERROR   = 2
    FAIL    = 3
    EMPTY   = 4
    NO_RES  = 5


class StopHandler(tornado.web.RequestHandler):
    def get(self):
        url = self.get_argument("url", None)
        if url is None or url == "":
            INFO("url is empty")
            self.write(str(RETURNCODE.EMPTY))
            return
        if stop_audio(url):
            self.write(RETURNCODE.FAIL)
        else:
            self.write(RETURNCODE.SUCCESS)


class ClearQeueuHandler(tornado.web.RequestHandler):
    def get(self):
        clear_audio_queue()
        self.write(RETURNCODE.SUCCESS)


class PlayHandler(tornado.web.RequestHandler):
    def get(self):
        url = self.get_argument("url", None)
        if url is None or url == "":
            INFO("url is empty")
            self.write(str(RETURNCODE.EMPTY))
            return

        is_inqueue = self.get_argument("inqueue", None)
        loop = self.get_argument("loop", None)
        if is_inqueue is None:
            if loop is None:
                play_audio(url)
            else:
                play_audio(url, int(loop))
        else:
            if loop is None:
                play_audio_inqueue(url)
            else:
                play_audio_inqueue(url, int(loop))
        self.write(str(RETURNCODE.SUCCESS))


class PauseHandler(tornado.web.RequestHandler):
    def get(self):
        url = self.get_argument("url", None)
        if url is None or url == "":
            if pause_audio(url):
                self.write(str(RETURNCODE.SUCCESS))
            else:
                self.write(str(RETURNCODE.ERROR))
        else:
            if pause_audio_queue():
                self.write(str(RETURNCODE.SUCCESS))
            else:
                self.write(str(RETURNCODE.ERROR))


# functions


def wait_util_player_finished(mp):
    while mp.time_pos < mp.length or mp.paused:
        print mp.time_pos
        sleep(0.5)


def play_audio(url, loop=-1):
    global mp_context

    def worker():
        mp.loadfile(url)
        INFO("%s is playing." % (url,))
        wait_util_player_finished(mp)
        mp.loop = -1
        if url in mp_context:
            del mp_context[url]

    if url in mp_context:
        mp = mp_context[url]
        if not mp is None:  # for thread-safe
            mp.loop = loop
            mp.loadfile(url)
            INFO("%s is playing." % (url,))
    else:
        mp = Player()
        mp.loop = loop
        mp_context[url] = mp
        t = threading.Thread(target=worker)
        t.setDaemon(True)
        t.start()

    return True


def play_audio_inqueue(url, loop=-1):
    global mp_queue
    mp_queue.put((url, loop))
    INFO("%s was added to queue." % (url,))


def stop_audio(url):
    global mp_context
    if not url in mp_context:
        WARN("%s is not playing" % (url, ))
        return False
    else:
        mp = mp_context[url]
        mp.stop()
        if mp in mp_context:
            del mp_context[url]
        return True


def pause_audio(url):
    global mp_context
    if not url in mp_context:
        WARN("%s is not playing" % (url, ))
        return False
    else:
        INFO("pause: " + url)
        mp = mp_context[url]
        mp.pause()
        return True


def pause_audio_queue():
    global mp_context
    INFO("pause audio queue.")
    mp = mp_context["queue"]
    mp.pause()
    return True


def clear_audio_queue():
    global mp_context
    global mp_queue

    with mp_queue.mutex:
        mp_queue.queue.clear()
    mp = mp_context["queue"]
    mp.stop()


def queue_worker():
    global mp_context
    global mp_queue

    mp = mp_context["queue"]
    while True:
        url, loop = mp_queue.get()
        mp.loop = loop
        mp.loadfile(url)
        wait_util_player_finished(mp)
        mp.loop = -1
        mp_queue.task_done()


def init_queue_player():
    mp_context["queue"] = Player()
    t = threading.Thread(target=queue_worker)
    t.setDaemon(True)
    t.start()


mp_context = {}
mp_queue = Queue()

application = tornado.web.Application([
    (r"/play", PlayHandler),
    (r"/clear", ClearQeueuHandler),
    (r"/stop", StopHandler),
    (r"/pause", PauseHandler),
])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
                    description='audio_server.py -p port')
    parser.add_argument('-p',
                        action="store",
                        dest="port",
                        default="8001",
                        )
    port = parser.parse_args().port
    INFO("bind to %s " % (port))

    signal.signal(signal.SIGINT, signal_handler)
    application.listen(port)
    init_queue_player()
    tornado.ioloop.PeriodicCallback(try_exit, 100).start()
    tornado.ioloop.IOLoop.instance().start()
