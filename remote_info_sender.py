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
import traceback
import time
from Queue import Queue, Empty
import urllib, urllib2
import json
import hashlib

import zmq

from util.Res import Res
from util.log import *
from vendor.baidu_push.Channel import *
from vendor.xg_push import xinge
from vendor.mipush import mipush

PUSH_apiKey = "7P5ZCG6WTAGWr5TuURBgndRH"                                             
PUSH_secretKey = "gggk30ubCSFGM5uXYfwGll4vILlnQ0em"                                  
PUSH_user_id = "4355409"   

XINGE_ACCESS_ID = 2100063377
XINGE_SECRET_KEY = "50618a8882f2dd7849a2f2bc68f41587"

MIPUSH_SECRET_KEY = "3b6uuQ2wE0ox80Tv4kV2fw=="
MIPUSH_PACKETAGE = "my.home.lehome"

class remote_info_sender:
    
    HOST = "http://lehome.sinaapp.com"

    def __init__(self, address):
        if not address is None:
            INFO("connect to server: %s " % (address))
            context = zmq.Context()
            self._sock = context.socket(zmq.SUB)
            self._sock.connect(address)
            self._sock.setsockopt(zmq.SUBSCRIBE, '')
            self.channel = Channel(PUSH_apiKey, PUSH_secretKey)
            self._mipush = mipush.MIPush(MIPUSH_SECRET_KEY)
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
                rep = self._sae_info(info)
                if len(rep) != 0:
                    DEBUG("remote_server rep:%s" % rep)
                    obj_rep = json.loads(rep)
                    if obj_rep['code'] == 200:
                        return True
                    else:
                        ERROR("send info error code:%d, desc:%s" %
                                (obj_rep['code'], obj_rep['desc']))
            except Exception, e:
                ERROR(e)
            return False
        else:
            ERROR("info is invaild.")
            return False

    def _push_info_baidu(self, info, tag_name):
        if not info is None and not info == "":
            DEBUG("baidu push info %s to remote server." % (info, ))
            # baidu push
            push_type = 2
            optional = {}                                                           
            optional[Channel.TAG_NAME] = tag_name                                   
            try:
                ret = self.channel.pushMessage(push_type, info, "key", optional)
                DEBUG("baidu push ret:%s" % ret)
            except Exception, e:
                ERROR(e)
                return False
            return True
        else:
            ERROR("info is invaild.")
            return False

    def _push_info_xg(self, info, tag_name):
        if not info is None and not info == "":
            DEBUG("xg push info %s to remote server." % (info, ))
            # xg push
            msg = self._build_msg(info)
            if msg is None:
                ERROR("xg msg is None.")
                return False
            try:
                # DEBUG("xg msg len: %d" % len(msg.content))
                ret = self.xinge_app.PushTags(0, (tag_name,), "OR", msg)
                DEBUG("xg push ret: %s,%s" % (ret[0], ret[1]))
            except Exception, e:
                ERROR(e)
                return False
            return True
        else:
            ERROR("info is invaild.")
            return False

    def _build_msg(self, content):
        msg = xinge.Message()
        msg.type = xinge.Message.TYPE_MESSAGE
        msg.content = content
        msg.expireTime = 5*3600
        # 自定义键值对，key和value都必须是字符串
        # msg.custom = {'aaa':'111', 'bbb':'222'}
        if len(msg.content) > 2500:
            INFO("xg msg reach max len:%d" % len(msg.content))
            try:
                msg_json = json.loads(msg.content)
                msg_id = hashlib.sha1(msg.content).hexdigest()
                msg_data = urllib.urlencode({'msg':msg_json["msg"].encode('utf-8')})

                url = remote_info_sender.HOST + "/api/text/%s?id=%s" \
                    % (msg_id, self._device_id,)
                rep = urllib2.urlopen(url, msg_data, timeout=10).read()
                rep_json = json.loads(rep)
                if rep_json["code"] != 200:
                    ERROR("xg api text rep code: %s" % rep_json["desc"])
                    return None

                INFO("api text success: %s", msg_id)
                msg_json["type"] = "long_msg"
                msg_json["msg"] = url
                msg.content = json.dumps(msg_json)
            except Exception, e:
                ERROR(traceback.format_exc())
                return None
        return msg
        
    def _push_info_xiaomi(self, info, tag_name):
        if not info is None and not info == "":
            DEBUG("xiaomi push info %s to remote server." % (info, ))
            # xiaomi push                                 
            try:
                ret = self._mipush.push_topic_passthrough(info, MIPUSH_PACKETAGE, tag_name)
                DEBUG("mi push ret:%s" % ret)
            except Exception, e:
                ERROR(e)
                return False
            return True
        else:
            ERROR("info is invaild.")
            return False
    
    def _sae_info(self, info):
        url = remote_info_sender.HOST + "/info/put?id=%s" \
                % (self._device_id,)
        rep = urllib2.urlopen(url, info, timeout=10).read()
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
            info = self._get_msg()
            DEBUG("_send_worker get: %s" % info)
            if not "\"heartbeat\"" in info:
            # info_object = json.loads(info)
            # msg_type = info_object['type']
            # if msg_type != "heartbeat":
                # self._push_info_xg(info, str(self._device_id))   
                # self._push_info_baidu(info, str(self._device_id))   
                self._push_info_xiaomi(info, str(self._device_id))
                self._send_info_to_server(info)

    def _put_worker(self):
        INFO("start waiting infos from home.")
        while True :
            try:
                info = self._sock.recv_string()
                self._put_msg(info)
                DEBUG("get info from home:%s" % info)
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
