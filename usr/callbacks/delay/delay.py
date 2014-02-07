#!/usr/bin/env python
# encoding: utf-8
from time import sleep
from lib.sound import LE_Sound
from util.LE_Res import LE_Res
import re
from util.LE_Util import parse_time


class time_callback:
    def callback(self,
            delay=None,
            delay_time=None,
            action=None,
            trigger=None, 
            ):
        print "* delay callback: %s, action: %s, target: %s" % (delay, action, target)
        return True, "pass"


class delay_callback:
    def callback(self,
            delay=None,
            delay_time=None,
            action=None,
            target=None, 
            ):
        print "* delay callback: %s, action: %s, target: %s" % (delay, action, target)

        if delay_time is None:
            return False, None

        minutes = parse_time(delay_time)
        if minutes is None:
            return False, None

        self._speaker.speak(minutes + u"分钟后执行。")
        sleep(int(minutes) * 60)

        self._rec.pause()
        LE_Sound.playmp3(
                        LE_Res.get_res_path("sound/com_stop")
                        )
        self._rec.resume()

        return True, "delay"
