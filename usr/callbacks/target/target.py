#!/usr/bin/env python
# encoding: utf-8

import glob
import types
import httplib
import json
import os
import errno
from datetime import datetime
from subprocess import PIPE, Popen
from util.Res import Res
from util.Util import parse_time
from lib.sound import Sound
from util.log import *


class target_callback:
    def callback(self,
            action=None,
            target=None,
            msg=None, 
            pre_value=None):
        DEBUG("* target callback: %s, message: %s pre_value: %s" %(target, msg, pre_value))
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

                self._home.setResume(True)
                filepath = path + datetime.now().strftime("%m-%d_%H:%M") + ".mp3"
                record = pre_value
                record(filepath)
                Sound.play(
                            Res.get_res_path("sound/com_stop")
                            )
                self._home.setResume(False)
        elif action == u"播放":
            self._home.setResume(True)

            if isinstance(pre_value, types.FunctionType):
                play = pre_value
                for idx, filepath in enumerate(glob.glob("usr/message/*.mp3")):
                    self._speaker.speak(u'第%d条留言' % (idx + 1))
                    play(filepath)

            Sound.play(
                        Res.get_res_path("sound/com_stop")
                        )

            self._home.setResume(False)
        return True, "pass"


class remind_callback:
    def callback(self,
            action=None,
            target=None,
            msg=None, 
            pre_value=None):

        if msg is None:
            return False, None

        minutes = parse_time(msg)
        print 'msg', msg, "minutes", minutes
        if minutes is None:
            return False, None

        self._home.setResume(True)
        p = Popen(["at", "now", "+", minutes, "minutes", "-M"],
                stdin=PIPE,
                stdout=PIPE,
                bufsize=1)
        url = Sound.get_request_url(Res.get_res_path("sound/com_bell"), 4)
        print >>p.stdin, "curl \"" + url + "\""
        print p.communicate("EOF")[0]

        Sound.play(
                    Res.get_res_path("sound/com_stop")
                    )
        self._home.setResume(False)
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
        alarm_time = parse_time(msg)
        print "alarm_time:", alarm_time
        if alarm_time is None:
            print "invalid alarm time:", msg
            return False, None

        self._home.setResume(True)
        p = Popen(["at", alarm_time, "-M"],
                stdin=PIPE,
                stdout=PIPE,
                bufsize=1)
        url = Sound.get_request_url(Res.get_res_path("sound/com_bell2"), 6)
        print >>p.stdin, "curl \"" + url + "\""
        print p.communicate("EOF")[0]

        Sound.play(
                    Res.get_res_path("sound/com_stop")
                    )
        self._home.setResume(False)
        self._speaker.speak(action + target + alarm_time)

        return True, "remind"
