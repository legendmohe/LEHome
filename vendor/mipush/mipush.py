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


import json
import httplib
import urllib
import time

ERR_OK = 0
ERR_PARAM = -1
ERR_HTTP = -100
ERR_RETURN_DATA = -101


class MIPushHelper(object):
    MIPUSH_HOST = 'api.xmpush.xiaomi.com'
    MIPUSH_PORT = 443
    MIPUSH_SECRET_KEY = ''
    TIMEOUT = 10
    HTTP_METHOD = 'POST'
    HTTP_HEADERS = {'Authorization': MIPUSH_SECRET_KEY, 'Content-Type': 'application/x-www-form-urlencoded'}

    STR_RET_CODE = 'code'
    STR_ERR_MSG = 'reason'
    STR_RESULT = 'data'

    @classmethod
    def SetServer(cls, host=MIPUSH_HOST, port=MIPUSH_PORT):
        cls.MIPUSH_HOST = host
        cls.MIPUSH_PORT = port

    @classmethod
    def SetAuthorization(cls, secretKey):
        cls.HTTP_HEADERS['Authorization'] = secretKey

    @classmethod
    def GenTimestamp(cls):
        return int(time.time())

    @classmethod
    def Request(cls, path, params):

        if 'Authorization' not in cls.HTTP_HEADERS or len(cls.HTTP_HEADERS['Authorization']) == 0:
            return ERR_PARAM, '', None

        httpClient = httplib.HTTPSConnection(cls.MIPUSH_HOST, cls.MIPUSH_PORT, timeout=cls.TIMEOUT)
        if cls.HTTP_METHOD == 'GET':
            httpClient.request(cls.HTTP_METHOD, ('%s?%s' % (path, urllib.urlencode(params))), headers=cls.HTTP_HEADERS)
        elif cls.HTTP_METHOD == 'POST':
            httpClient.request(cls.HTTP_METHOD, path, urllib.urlencode(params), headers=cls.HTTP_HEADERS)
        else:
            # invalid method
            return ERR_PARAM, '', None

        response = httpClient.getresponse()
        ret_code = ERR_RETURN_DATA
        err_msg = ''
        result = {}
        if 200 != response.status:
            ret_code = ERR_HTTP
        else:
            data = response.read()
            ret_dict = json.loads(data)
            if cls.STR_RET_CODE in ret_dict:
                ret_code = ret_dict[cls.STR_RET_CODE]
            if cls.STR_ERR_MSG in ret_dict:
                err_msg = ret_dict[cls.STR_ERR_MSG]
            if cls.STR_RESULT in ret_dict:
                result = ret_dict[cls.STR_RESULT]
        return ret_code, err_msg, result


class MIPush(object):
    PATH_PUSH_TAGS = '/v2/message/topic'

    def __init__(self, app_secret):
        self._secret = 'key=' + str(app_secret)
        MIPushHelper.SetAuthorization(self._secret)

    def push_topic_passthrough(self, payload, package_name, topic,
                               noti_type=-1, time_to_live=1000 * 3600):
        params = {
            'pass_through': 1,
            'payload': payload,
            'restricted_package_name': package_name,
            'topic': topic,
            'notify_type': noti_type,
            'time_to_live': int(time_to_live)
        }
        ret_code, err_msg, result = self.request(MIPush.PATH_PUSH_TAGS, params)
        if ret_code != 0:
            print ret_code, err_msg, result
        else:
            print ret_code, err_msg, result
        return ret_code

    def request(self, path, params):
        return MIPushHelper.Request(path, params)


def main():
    mipush = MIPush('3b6uuQ2wE0ox80Tv4kV2fw==')
    mipush.push_topic_passthrough('test', 'my.home.lehome', '12345678')


if __name__ == "__main__":
    main()
