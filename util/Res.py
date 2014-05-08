#!/usr/bin/env python
# encoding: utf-8

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
    def init(path):
        path = os.path.join(Res.base_path, path)
        with open(path) as init_file:
            init_json = json.load(init_file)
            if not init_json:
                ERROR("error: invaild init.json.")
                return
            else:
                Res.settings = init_json
        return Res.settings
