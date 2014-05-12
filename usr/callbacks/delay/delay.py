#!/usr/bin/env python
# encoding: utf-8


import threading
import time
from datetime import datetime
from lib.sound import Sound
from util.Res import Res
from util.Util import parse_time, cn2dig, gap_for_timestring
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
        if delay_time is None:
            self._home.publish_msg(cmd, u"时间格式错误")
            return False, None

        if delay_time.endswith(u'点') or \
           delay_time.endswith(u'分'):
            t = gap_for_timestring(delay_time)
        elif delay_time.endswith(u"分钟"):
            t = int(cn2dig(delay_time[:-2]))*60
        elif delay_time.endswith(u"小时"):
            t = int(cn2dig(delay_time[:-2]))*60*60
        else:
            self._home.publish_msg(cmd, u"时间格式错误")
            return False
        info = delay_time + u"执行"
        self._home.publish_msg(cmd, info)
        INFO("thread wait for %d sec" % (t, ))

        threading.current_thread().waitUtil(t)
        if threading.current_thread().stopped():
            return False

        self._home.setResume(True)
        Sound.play(
            Res.get_res_path("sound/com_stop")
        )
        self._home.setResume(False)
        return True
