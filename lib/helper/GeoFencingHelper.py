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


import time
import urllib, urllib2


from util.log import *


class GeoFencingHelper(object):

    def __init__(self, server_address):
        self.server_address = server_address

    def send_geo_report(self, content):
        if not content is None and not content == "":
            DEBUG("send geo report %s to geo fencing server." % (content, ))
            try:
                url = self.server_address + "/report"
                enc_data = urllib.urlencode(content)
                response = urllib2.urlopen(url,
                                            enc_data,
                                            timeout=5).read()
            except urllib2.HTTPError, e:
                ERROR(e)
                return False
            except urllib2.URLError, e:
                ERROR(e)
                return False
            except Exception, e:
                ERROR(e)
                return False
            else:
                DEBUG("geo server response: " + response)
                return True
        else:
            ERROR("conent is invaild.")
            return False
