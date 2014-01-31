#!/usr/bin/env python
# encoding: utf-8
from time import sleep
from lib.sound import LE_Sound
from util.LE_Res import LE_Res

class time_callback:
    def callback(self,
            delay=None,
            action=None,
            trigger=None, 
            ):
        print "* delay callback: %s, action: %s, target: %s" % (delay, action, target)
        return True, "pass"

class delay_callback:
    def callback(self,
            delay=None,
            action=None,
            target=None, 
            ):
        print "* delay callback: %s, action: %s, target: %s" % (delay, action, target)

        if delay is None:
            return False, "delay"

        minutes = "1"
        if delay.startswith(u"一分"):
            minutes = "1"
        elif delay.startswith(u"两分"):
            minutes = "2"
        elif delay.startswith(u"三分"):
            minutes = "3"
        elif delay.startswith(u"五分"):
            minutes = "5"
        elif delay.startswith(u"十分"):
            minutes = "10"
        elif delay.startswith(u"十五分"):
            minutes = "15"
        else:
            m = re.match(r"(\d+)分.*", delay)
            if m:
                minutes = m.group(1)
            else:
                return False, "delay"

        self._speaker.speak(minutes + u"分钟后执行。")
        sleep(int(minutes) * 60)

        self._rec.pause()
        LE_Sound.playmp3(
                        LE_Res.get_res_path("sound/com_stop")
                        )
        self._rec.resume()

        return True, "delay"
