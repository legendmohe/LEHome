#!/usr/bin/env python
# encoding: utf-8


import threading
import time
from datetime import datetime
from lib.sound import Sound
from util.Res import Res
from util.Util import parse_time, cn2dig
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

        print delay_time

        if delay_time.endswith(u'点') \
                or delay_time.endswith(u'分'):
            t = 0
            delay_time = delay_time[1:]
            is_pm = False
            if delay_time.startswith(u"上午"):
                t = t + 0
                delay_time = delay_time[2:]
            elif delay_time.startswith(u"下午"):
                t = t + 12*60*60
                is_pm = True
                delay_time = delay_time[2:]

            t_list = parse_time(delay_time).split(":")
            target_hour = int(t_list[0])
            if is_pm:
                target_hour = target_hour + 12
            target_min = int(t_list[1])
            now = datetime.now()
            cur_hour = now.hour
            cur_min = now.minute
            if cur_hour < target_hour or \
                    (cur_hour <= target_hour and cur_min <= target_min):
                t = (target_hour - cur_hour)*60*60 + (target_min - cur_min)*60
            else:
                t = 24*60*60  \
                    - ((cur_hour - target_hour)*60*60 + (cur_min - target_min)*60)
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
