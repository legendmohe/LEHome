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


import os
import json
from util.log import *

class Res:
    settings = {}
    base_path = os.path.abspath(os.path.join(os.path.dirname(__file__),"../usr/"))
    
    @staticmethod
    def get(name):
        elem = Res.settings
        try:
            for x in name.strip("/").split("/"):
                elem = elem.get(x)
        except:
            ERROR("invaild get method params : " + name)
            pass
        return elem

    @staticmethod
    def get_res_path(elem):
        elem = os.path.join(Res.base_path + '/res/', Res.get(elem))
        return elem

    @staticmethod
    def init(path, force=False):
        if force == False and len(Res.settings) != 0:
            return Res.settings
        path = os.path.join(Res.base_path, path)
        with open(path) as init_file:
            init_json = json.load(init_file)
            if not init_json:
                ERROR("error: invaild init.json.")
                return
            else:
                Res.settings = init_json
        return Res.settings
