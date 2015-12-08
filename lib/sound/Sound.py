#!usr/bin/env python
#coding=utf-8
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



import urllib
import urllib2
from util.log import *


AUDIO_SERVER_ADDRESS = None

def get_play_request_url(path, inqueue, channel, loop=-1):
    global AUDIO_SERVER_ADDRESS
    if AUDIO_SERVER_ADDRESS is None:
        WARN("audio server address is empty.")
        return None
    values = {'url': path}
    if inqueue is not None:
        values["inqueue"] = True
    if channel is not None:
        values["channel"] = channel
    if not loop == -1:
        values["loop"] = loop
    data = urllib.urlencode(values)
    return AUDIO_SERVER_ADDRESS + '/play?' + data


def get_clear_request_url():
    global AUDIO_SERVER_ADDRESS
    if AUDIO_SERVER_ADDRESS is None:
        WARN("audio server address is empty.")
        return None
    return AUDIO_SERVER_ADDRESS + '/clear'


def get_volume_url():
    global AUDIO_SERVER_ADDRESS
    if AUDIO_SERVER_ADDRESS is None:
        WARN("audio server address is empty.")
        return None
    return AUDIO_SERVER_ADDRESS + '/volume'


def play(path, inqueue=False, channel='default', loop=-1):
    url = get_play_request_url(path, inqueue, channel, loop)
    if url is None:
        return
    INFO("sending audio url: " + url)
    try:
        response = urllib2.urlopen(url).read()
    except urllib2.HTTPError, e:
        INFO(e)
        WARN("audio server address is invaild")
    except urllib2.URLError, e:
        INFO(e)
        WARN("audio server unavailable.")
    else:
        INFO("audio response: " + response)

def notice(path, inqueue=False, loop=-1):
    play(path, inqueue, channel='notice', loop=loop)

def stop(path):
    pass

def set_volume(value):
    url = get_volume_url()
    if url is None:
        return
    response = None
    try:
        value = int(value)
        if value < 0:
            value = 0
        elif value > 100:
            value = 100
        INFO("setting audio volume: %s" % value)
        data = {"v":value}
        enc_data = urllib.urlencode(data)
        response = urllib2.urlopen(url, enc_data).read()
    except urllib2.HTTPError, e:
        INFO(e)
        WARN("audio server address is invaild")
    except urllib2.URLError, e:
        INFO(e)
        WARN("audio server unavailable.")
    except Exception, e:
        ERROR(e)
    else:
        INFO("audio set volume response: " + response)
    return response

def get_volume():
    url = get_volume_url()
    if url is None:
        return
    INFO("getting audio volume: %s" % url)
    response = None
    try:
        response = urllib2.urlopen(url).read()
    except urllib2.HTTPError, e:
        INFO(e)
        WARN("audio server address is invaild")
    except urllib2.URLError, e:
        INFO(e)
        WARN("audio server unavailable.")
    else:
        INFO("audio response: " + response)
    INFO("getting audio volume: %s" % response)
    return response

def clear_queue():
    url = get_clear_request_url()
    if url is None:
        return
    INFO("cleaning audio queue")
    try:
        response = urllib2.urlopen(url).read()
    except urllib2.HTTPError, e:
        INFO(e)
        WARN("audio server address is invaild")
    except urllib2.URLError, e:
        INFO(e)
        WARN("audio server unavailable.")
    else:
        INFO("audio response: " + response)
