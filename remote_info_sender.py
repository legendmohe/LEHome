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



import argparse
import threading
import time
from Queue import Queue, Empty
import urllib, urllib2
import json
import zmq
from util.Res import Res
from util.log import *
from vender.baidu_push.Channel import *

PUSH_apiKey = "7P5ZCG6WTAGWr5TuURBgndRH"                                             
PUSH_secretKey = "gggk30ubCSFGM5uXYfwGll4vILlnQ0em"                                  
PUSH_user_id = "4355409"   

class remote_info_sender:
    
    HOST = "http://lehome.sinaapp.com"

    def __init__(self, address):
        if not address is None:
            INFO("connect to server: %s " % (address))
            context = zmq.Context()
            self._sock = context.socket(zmq.SUB)
            self._sock.connect(address)
            self._sock.setsockopt(zmq.SUBSCRIBE, '')

            self._msg_queue = Queue()

            settings = Res.init("init.json")
            self._device_id = settings['id']
        else:
            ERROR("address is empty")

    def _send_info_to_server(self, info):
        if not info is None and not info == "":
            DEBUG("send info %s to remote server." % (info, ))

            try:
                info = info.encode('utf-8')
                ret = self._push_info(info, str(self._device_id))   
                DEBUG("push ret:%s" % ret)
                rep = self._sae_info(info)
                if len(rep) != 0:
                    DEBUG("remote_server rep:%s" % rep)
                    if rep == 'ok':
                        return True
                ERROR("invaild rep:" % rep)
            except Exception, e:
                ERROR(e)
            return False
        else:
            ERROR("info is invaild.")
            return False

    def _push_info(self, info, tag_name):
        # baidu push
        c = Channel(PUSH_apiKey, PUSH_secretKey)                                              
        push_type = 2                                                               
        optional = {}                                                           
        optional[Channel.TAG_NAME] = tag_name                                   
        ret = c.pushMessage(push_type, info, "key", optional)
        return ret
    
    def _sae_info(self, info):
        url = remote_info_sender.HOST + "/info/put/%s?id=%s" \
                % (urllib.quote_plus(info) , self._device_id)
        req = urllib2.Request(url)
        rep = urllib2.urlopen(req, timeout=10).read()
        return rep

    def _put_msg(self, msg):
        self._msg_queue.put(msg)

    def _get_msg(self):
        msg = self._msg_queue.get(
                                block=True,
                                ) # block!
        self._msg_queue.task_done()
        return msg

    def start(self):
        if self._msg_queue is None:
            ERROR("remote_info_sender start faild.")
            return

        send_t = threading.Thread(
                    target=self._send_worker
                    )
        send_t.daemon = True
        send_t.start()
        self._put_worker()

    def _send_worker(self):
        while True:
            msg = self._get_msg()
            self._send_info_to_server(msg)

    def _put_worker(self):
        INFO("start waiting infos from home.")
        while True :
            try:
                info = self._sock.recv_string()
                DEBUG("get info from home:%s" % info)
                info_object = json.loads(info)
                
                msg_seq  = info_object['seq']
                msg_msg  = info_object['msg']
                msg_type = info_object['type']
                msg_ts   = info_object["ts"]
                if msg_type != "heartbeat":
                    # unicode !
                    DEBUG("put msg to queue:%s" % msg_msg)
                    self._put_msg(u"%s,%s,%s" % (msg_seq, msg_ts, msg_msg))
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception, ex:
                ERROR(ex)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
                    description='remote_info_sender.py -a address')
    parser.add_argument('-a',
                        action="store",
                        dest="address",
                        default="tcp://localhost:9000",
                        )
    args = parser.parse_args()
    address = args.address

    INFO("remote info sender is activate.")
    remote_info_sender(address).start()
