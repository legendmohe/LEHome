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



import threading
from lib.sound import Sound
from util.Res import Res
from util import Util
from lib.model import Callback
from util.log import *


class time_callback(Callback.Callback):
    def callback(self,
            delay=None,
            delay_time=None,
            action=None,
            trigger=None, 
            ):
        DEBUG("* delay callback: %s, action: %s, target: %s" % (delay, action, target))
        return True, pre_value


class delay_callback(Callback.Callback):
    def callback(self, cmd, delay_time, action, target, msg):
        if delay_time is None or len(delay_time) == 0:
            self._home.publish_msg(cmd, u"时间格式错误")
            return False, None

        t = None
        if delay_time.endswith(u"秒") or delay_time.endswith(u"秒钟"):
            t = int(Util.cn2dig(delay_time[:-1]))
        elif delay_time.endswith(u"分钟"):
            t = int(Util.cn2dig(delay_time[:-2]))*60
        elif delay_time.endswith(u"小时"):
            t = int(Util.cn2dig(delay_time[:-2]))*60*60
        else:
            t = Util.gap_for_timestring(delay_time)
        if t is None:
            WARN("error delay_time format")
            self._home.publish_msg(cmd, u"时间格式错误:" + delay_time)
            return False, None
        info = delay_time + u"执行: %s%s%s" % (
                                                Util.xunicode(action),
                                                Util.xunicode(target),
                                                Util.xunicode(msg)
                                                )
        # self._home.publish_msg(cmd, info)  # noise
        DEBUG("delay wait for %d sec" % (t, ))

        threading.current_thread().waitUtil(t)
        if threading.current_thread().stopped():
            return False
        return True
