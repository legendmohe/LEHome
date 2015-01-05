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

def get_play_request_url(path, inqueue=False, loop=-1):
    global AUDIO_SERVER_ADDRESS
    if AUDIO_SERVER_ADDRESS is None:
        WARN("audio server address is empty.")
        return None
    values = {'url': path}
    if inqueue:
        values["inqueue"] = True
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


def play(path, inqueue=False, loop=-1):
    url = get_play_request_url(path, inqueue, loop)
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


def stop(path):
    pass

def set_volume(value):
    url = get_volume_url()
    if url is None:
        return
    INFO("setting audio volume: %s" % value)
    response = None
    try:
        data = {"v":value}
        enc_data = urllib.urlencode(data)
        response = urllib2.urlopen(url, enc_data).read()
    except urllib2.HTTPError, e:
        INFO(e)
        WARN("audio server address is invaild")
    except urllib2.URLError, e:
        INFO(e)
        WARN("audio server unavailable.")
    else:
        INFO("audio set volume response: " + response)
    return response

def get_volume():
    url = get_volume_url()
    if url is None:
        return
    INFO("getting audio volume: %s" % value)
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
