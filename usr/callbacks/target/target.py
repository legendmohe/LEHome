#!/usr/bin/env python
# encoding: utf-8

import glob
import types
import httplib
import json
import os
import errno
import re
from datetime import datetime
from subprocess import PIPE, Popen
from lib.sound import LE_Sound
from util.LE_Res import LE_Res
from lib.speech.LE_Speech import LE_Speech2Text
from lib.sound import LE_Sound


def minutes_msg2num(msg):
    minutes = "2"
    if msg.startswith(u"一分"):
        minutes = "1"
    elif msg.startswith(u"两分"):
        minutes = "2"
    elif msg.startswith(u"三分"):
        minutes = "3"
    elif msg.startswith(u"五分"):
        minutes = "5"
    elif msg.startswith(u"十分"):
        minutes = "10"
    elif msg.startswith(u"十五分"):
        minutes = "15"
    else:
        m = re.match(r"(\d+)分.*", msg)
        if m:
            minutes = m.group(1)
        else:
            return None
    return minutes


def hours_msg2num(msg):
    hours = "2"
    if msg.startswith(u"一点"):
        hours = "1"
    elif msg.startswith(u"两点"):
        hours = "2"
    elif msg.startswith(u"三点"):
        hours = "3"
    elif msg.startswith(u"五点"):
        hours = "5"
    elif msg.startswith(u"十点"):
        hours = "10"
    elif msg.startswith(u"十五点"):
        hours = "15"
    else:
        m = re.match(r"(\d+)点.*", msg)
        if m:
            hours = m.group(1)
        else:
            return None
    return hours

class target_callback:
    def callback(self,
            action=None,
            target=None,
            msg=None, 
            pre_value=None):
        print "* target callback: %s, message: %s pre_value: %s" %(target, msg, pre_value)
        return True, "pass"

class douban_callback:

    __music_table = {
        "华语":"1",
        "欧美":"2",
        "70":"3",
        "80":"4",
        "90":"5",
        "粤语":"6",
        "摇滚":"7",
        "民谣":"8",
        "轻音乐":"9",
        "电影原声":"10",
        "爵士":"13",
        "电子":"14",
        "说唱":"15",
        "R&B":"16",
        "日语":"17",
        "韩语":"18",
        "女声":"20",
        "特仑苏":"21",
        "法语":"22",
        "豆瓣音乐人":"26",
                }
    
    def callback(self,
            action=None,
            target = None,
            msg = None, 
            pre_value = None):
        if isinstance(pre_value, types.FunctionType):
            music_id = "9" # 轻音乐
            if msg in self.__music_table:
                music_id = self.__music_table[msg]
            play = pre_value 
            httpConnection = httplib.HTTPConnection('douban.fm')
            httpConnection.request('GET', '/j/mine/playlist?type=n&channel=' + music_id)
            song = json.loads(httpConnection.getresponse().read())['song']
            play(song[0]['url'])
        return True, "pass"

class message_callback:
    def callback(
            self,
            action=None,
            target=None,
            msg=None, 
            pre_value=None):
        if action == u"记录":
            if isinstance(pre_value, types.FunctionType):
                path = "usr/message/"
                try:
                    os.makedirs(path)
                except OSError as exc:
                    if exc.errno == errno.EEXIST and os.path.isdir(path):
                        pass
                    else:
                        print exc
                        return True, "pass"

                self._rec.pause()
                filepath = path + datetime.now().strftime("%m-%d_%H:%M") + ".mp3"
                record = pre_value
                record(filepath)
                LE_Sound.playmp3(
                                LE_Res.get_res_path("sound/com_stop")
                                )
                self._rec.resume()
        elif action == u"播放":
            self._rec.pause()

            if isinstance(pre_value, types.FunctionType):
                play = pre_value
                for idx, filepath in enumerate(glob.glob("usr/message/*.mp3")):
                    self._speaker.speak(u'第%d条留言' % (idx + 1))
                    play(filepath)

            LE_Sound.playmp3(
                            LE_Res.get_res_path("sound/com_stop")
                            )

            self._rec.resume()
        return True, "pass"


class remind_callback:
    def callback(self,
            action=None,
            target=None,
            msg=None, 
            pre_value=None):

        if msg is None:
            return False, None

        minutes = minutes_msg2num(msg)
        if minutes is None:
            return False, None

        self._rec.pause()
        p = Popen(["at", "now", "+", minutes, "minutes"],
                stdin=PIPE,
                stdout=PIPE,
                bufsize=1)
        print >>p.stdin, "play " + LE_Res.get_res_path("sound/com_bell") + " repeat 4"
        print p.communicate("EOF")[0]

        LE_Sound.playmp3(
                        LE_Res.get_res_path("sound/com_stop")
                        )
        self._rec.resume()
        self._speaker.speak(action + target + minutes + u"分钟")

        return True, "remind"

class alarm_callback:
    def callback(self,
            action=None,
            target=None,
            msg=None, 
            pre_value=None):

        if msg is None:
            return False, None

        hours = hours_msg2num(msg)
        if hours is None:
            print "alarm action must set hours."
            return False, None
        mins = minutes_msg2num(msg)
        if mins is None:
            mins = "00"

        self._rec.pause()
        p = Popen(["at", hours + ":" + mins],
                stdin=PIPE,
                stdout=PIPE,
                bufsize=1)
        print >>p.stdin, "play " + LE_Res.get_res_path("sound/com_bell2") + " repeat 6"
        print p.communicate("EOF")[0]

        LE_Sound.playmp3(
                        LE_Res.get_res_path("sound/com_stop")
                        )
        self._rec.resume()
        self._speaker.speak(action + target + hours + u"点" + mins + u"分")

        return True, "remind"
