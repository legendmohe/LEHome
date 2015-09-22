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


import sys
import time
import json

import redis

HISTORY_CMD_KEY = "lehome:cmd_history_list"

r = redis.Redis(host='localhost', port=6379)

print "dbsize:", r.dbsize()
print "num of keys:", r.keys()
print "volume:", r.get("lehome:last_volume")

historys = r.lrange(HISTORY_CMD_KEY, 0, -1)
print "history size:", len(historys)

# r.delete(HISTORY_CMD_KEY)

for i in range(1, 10):
    print historys[-i]

look_up_dict = {}
for item in historys:
    item = item.split(":")
    stmp = int(item[0])
    cmd = item[1]
    if cmd not in look_up_dict:
        look_up_dict[cmd] = {'count': 0}
    look_up_dict[cmd]['count'] = look_up_dict[cmd]['count'] + 1

print "dict size:", len(look_up_dict)
with open("../usr/history.json", "w") as f:
    f.write(json.dumps(look_up_dict))
