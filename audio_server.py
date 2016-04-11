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


# alsa settings refer to:
# https://gist.github.com/legendmohe/83ba17c1e9b9c46480d2

import threading
import subprocess
import os
import signal
from Queue import Queue
from time import sleep
import argparse

import tornado.ioloop
import tornado.web
import alsaaudio

from util.log import *

SOUNDCARD_NAME = u'ALSA'

class RETURNCODE:
    SUCCESS = '1'
    ERROR   = '2'
    FAIL    = '3'
    EMPTY   = '4'
    NO_RES  = '5'


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


class VolumeHandler(tornado.web.RequestHandler):

    def initialize(self):
        cards = alsaaudio.cards()
        INFO(cards)
        card_idx = cards.index(SOUNDCARD_NAME)
        self._m = alsaaudio.Mixer(control='PCM', cardindex=card_idx)
        INFO("use card %d." % card_idx)

    def get(self):
        DEBUG(u"正在获取音量值")
        try:
            volumes = self._m.getvolume()
            INFO("get volumes:%s" % volumes)
            volume = str(int(volumes[0]))
            DEBUG(u"当前音量值为：%s" % volume)
            self.write(volume)
        except Exception, e:
            ERROR(e)
        self.write("")

    def post(self):
        v_str = self.get_argument("v", default=None, strip=False)
        if v_str is None:
            self.write("-1")
            WARN(u"请输入音量值")
            return
        try:
            DEBUG("set volume:%s" % v_str)
            volume = int(v_str)
        except ValueError:
            try:
                volume = float(v_str)
                self.write("-2")
                ERROR(u"音量值必须为整数")
                return
            except ValueError:
                volume = -1
        if volume == -1:
            self.write("-3")
            ERROR(u"音量值无效：%s" % msg)
            return
        self._m.setvolume(volume)
        INFO(u"设置音量值为：%s" % str(volume))
        self.write(RETURNCODE.SUCCESS)


class PlayHandler(tornado.web.RequestHandler):
    def get(self):
        url = self.get_argument("url", None)
        if url is None or url == "":
            INFO("url is empty")
            self.write(str(RETURNCODE.EMPTY))
            return

        is_inqueue = self.get_argument("inqueue", None)
        channel = self.get_argument("channel", "default")
        loop = self.get_argument("loop", None)
        if is_inqueue is None:
            if loop is None:
                play_audio(url, channel)
            else:
                play_audio(url, channel, int(loop))
        else:
            if loop is None:
                play_audio_inqueue(url, channel)
            else:
                play_audio_inqueue(url, channel, int(loop))
        self.write(str(RETURNCODE.SUCCESS))


# ============== functions ============


def worker(play_url, channel, loop):
    global mp_context, mixer_normal, mixer_notice

    cmd = [
            'sudo',
            'mplayer',
            '-ao', 'alsa:device=%s' % channel,
            play_url,
            '-loop', str(loop)]
    INFO("play cmd:%s" % cmd)
    nor_vol = mixer_normal.getvolume()[0]
    if channel == 'notice':
        mixer_normal.setvolume(int(nor_vol*0.8))
    with open(os.devnull, 'w') as tempf:
        player = subprocess.Popen(cmd, stdout=tempf, stderr=tempf)
        mp_context[play_url] = player
        print "player create: " + str(player.pid)
        player.communicate()
    if play_url in mp_context:
        del mp_context[play_url]
    print "play finished:%s" % (play_url,)
    mixer_normal.setvolume(nor_vol)


def play_audio(url, channel='default', loop=1):
    global mp_context

    if url in mp_context:
        mp = mp_context[url]
        if not mp is None:  # for thread-safe
            mp.terminate()
    t = threading.Thread(target=worker, args=(url, channel, loop))
    t.setDaemon(True)
    t.start()

    return True


def play_audio_inqueue(url, channel='default', loop=1):
    global mp_queue
    mp_queue.put((url, channel, loop))
    INFO("%s was added to queue." % (url,))


def stop_audio(url):
    global mp_context
    if not url in mp_context:
        WARN("%s is not playing" % (url, ))
        return False
    else:
        mp = mp_context[url]
        if not mp is None:  # for thread-safe
            mp.terminate()
            if url in mp_context:
                del mp_context[url]
        return True


def clear_audio_queue():
    global mp_context
    global mp_queue

    with mp_queue.mutex:
        mp_queue.queue.clear()
    if "queue" in  mp_context:
        mp_context["queue"].terminate()
        del mp_context["queue"]


def queue_worker():
    global mp_context, mixer_normal, mixer_notice
    global mp_queue

    while True:
        url, channel, loop = mp_queue.get()
        print "get from queue:%s \n channel:%s" % (str(url), channel)
        cmd = [
                'sudo',
                'mplayer',
                '-ao', 'alsa:device=%s' % channel,
                url,
                '-loop', str(loop)]
        # print cmd
        INFO("queue play cmd:%s" % cmd)
        nor_vol = mixer_normal.getvolume()[0]
        if channel == 'notice':
            # INFO("set nor_vol to 20")
            mixer_normal.setvolume(int(nor_vol*0.8))
        with open(os.devnull, 'w') as tempf:
            player = subprocess.Popen(cmd, stdout=tempf, stderr=tempf)
            mp_context["queue"] = player
            player.communicate()
            print url + u" stopped."
            if "queue" in  mp_context:
                del mp_context["queue"]
        mixer_normal.setvolume(nor_vol)
        mp_queue.task_done()
    sleep(1)


def init_queue_player():
    t = threading.Thread(target=queue_worker)
    t.setDaemon(True)
    t.start()


mp_context = {}
mp_queue = Queue()
mixer_normal = alsaaudio.Mixer(control='chan_norl_amp')
mixer_notice = alsaaudio.Mixer(control='chan_noti_amp')
# http://stackoverflow.com/questions/17101502/how-to-stop-the-tornado-web-server-with-ctrlc
is_closing = False
def signal_handler(signum, frame):
    global is_closing
    is_closing = True


def try_exit():
    global is_closing, mp_context
    if is_closing:
        # clean up here
        tornado.ioloop.IOLoop.instance().stop()
        logging.info('exit success')
        for url in mp_context:
            mp = mp_context[url]
            mp.terminate()


application = tornado.web.Application([
    (r"/play", PlayHandler),
    (r"/clear", ClearQeueuHandler),
    (r"/stop", StopHandler),
    (r"/volume", VolumeHandler),
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
