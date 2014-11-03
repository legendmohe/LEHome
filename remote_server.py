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
import threading
import logging
import logging.handlers
import collections
import tornado.ioloop
import tornado.web

"""
logging
"""

log_file_name = 'remote.log'
logger = logging.getLogger('RemoteLog')
handler = logging.handlers.RotatingFileHandler(log_file_name, maxBytes=20*1024*1024)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.setLevel(logging.INFO)
logger.addHandler(handler)
# logger.propagate = False # now if you use logger it will not log to console.

DEBUG    = logger.debug
INFO     = logger.info
WARN     = logger.warning
ERROR    = logger.error
CRITICAL = logger.critical

"""
signal handling
"""

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

class remote_cb(object):

    """remote server control board"""

    def __init__(self):
        self._cmd_queue = collections.deque(maxlen=100)
        self._cmd_lock = threading.Lock()
        self._publish_lock = threading.Lock()
        self._info_queue = collections.deque(maxlen=500)

    def cmd_number(self):
        return len(self._cmd_queue)

    def info_number(self):
        return len(self._info_queue)

    def put_cmd(self, cmd):
        if cmd is not None and len(cmd) != 0:
            with self._cmd_lock:
                self._cmd_queue.append(cmd)
            return True
        else:
            print "invaild cmd:%s" % cmd
            return False

    def pop_cmd(self):
        try:
            return self._cmd_queue.popleft(cmd)
        except IndexError:
            return None

    def pop_all_cmd(self):
        with self._cmd_lock:
            cmds = list(self._cmd_queue)
            self._cmd_queue.clear()
            return cmds

    def put_info(self, info):
        if info is not None and len(info) == 2:
            self._info_queue.append(info)
            return True
        else:
            print "invaild info:%s" % info
            return False

    def pop_info(self):
        try:
            return self._info_queue.popleft(info)
        except indexerror:
            return none

    def pop_info_start_from(self, index):
        infos = list(self._info_queue)
        start = 0
        for idx, info in infos:
            if idx >= index:
                break
            else:
                start += 1
        return infos[start:len(infos)]

"""
initialize
"""
def initialize():
    global remote_cb
    remote_cb = remote_cb()


class CmdPutHandler(tornado.web.RequestHandler):

    def get(self, cmd):
        global remote_cb
        if not cmd is None and not cmd == "":
            INFO("send cmd %s to home." % (cmd, ))
            if(remote_cb.put_cmd(cmd)):
                rep = "ok"
            else:
                rep = "error"
            self.write(rep)
        else:
            self.write("error")


class CmdFetchHandler(tornado.web.RequestHandler):

    def get(self):
        global remote_cb
        if remote_cb.info_number() != 0:
            INFO("server fetch all cmds: %d" % remote_cb.cmd_number())
            cmds = remote_cb.pop_all_cmd()
            if len(cmds) != 0:
                self.write("|".join(cmds))
            else:
                self.write("")
        else:
            self.write("")


class CmdSizeHandler(tornado.web.RequestHandler):

    def get(self):
        global remote_cb
        return remote_cb.cmd_number()


class InfoFetchHandler(tornado.web.RequestHandler):

    def get(self, start_index):
        if int(start_index) < 0:
            self.write("")
            return
        infos = remote_cb.pop_info_start_from(start_index)
        if len(infos) != 0:
            self.write("|".join([info[1] for info in infos]))
        else:
            self.write("")


class InfoPutHandler(tornado.web.RequestHandler):

    def get(self, info_pair):
        global remote_cb
        if info_pair is None or len(info_pair) < 0:
            self.write("error")
            return
        pair = info_pair.split(",")
        if len(pair) != 2:
            self.write("error")
            return
        remote_cb.put_info(tuple(pair))
        self.write("ok")


class InfoSizeHandler(tornado.web.RequestHandler):

    def get(self):
        global remote_cb
        return remote_cb.info_number()


class CmdListHandler(tornado.web.RequestHandler):

    def get(self):
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
                    description='remote_server.py -b http_server_port')
    parser.add_argument('-b',
                        action="store",
                        dest="http_port",
                        default="8002",
                        )

    args = parser.parse_args()
    http_port = args.http_port

    signal.signal(signal.SIGINT, signal_handler)

    INFO("http command server is activate.")
    initialize()
    application = tornado.web.Application([
                (r"/cmd/put/([^/]*)", CmdPutHandler),
                (r"/cmd/fetch", CmdFetchHandler),
                (r"/cmd/size", CmdSizeHandler),
                (r"/info/put/([^/]*)", InfoPutHandler),
                (r"/info/fetch/([^/]*)", InfoFetchHandler),
                (r"/info/size", InfoSizeHandler),
                (r"/cmdlist", CmdListHandler),
                ])
    application.listen(http_port)
    INFO("listening to %s " % (http_port))
    tornado.ioloop.PeriodicCallback(try_exit, 100).start()
    tornado.ioloop.IOLoop.instance().start()
