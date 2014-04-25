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
from util.Util import parse_time, cn2dig
from lib.sound import Sound
from util.log import *
from lib.model import Callback


class target_callback(Callback.Callback):
    def callback(self,
            action=None,
            target=None,
            msg=None, 
            pre_value=None):
        INFO("* target callback: %s, message: %s pre_value: %s" %(target, msg, pre_value))
        return True, "pass"

class douban_callback(Callback.Callback):

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

class message_callback(Callback.Callback):
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
                        ERROR(exc)
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


class remind_callback(Callback.Callback):
    def callback(self,
            action=None,
            target=None,
            msg=None, 
            pre_value=None):

        if msg is None:
            return False, None

        minutes = parse_time(msg)
        print msg, " to ", minutes
        if minutes is None:
            return False, None

        self._home.setResume(True)
        p = Popen(["at", "now", "+", minutes, "minutes"],
                stdin=PIPE,
                stdout=PIPE,
                bufsize=1)
        url = Sound.get_play_request_url(Res.get_res_path("sound/com_bell"), 4)
        print >>p.stdin, "mpg123 \"" + url + "\""
        print p.communicate("EOF")[0]

        Sound.play(
                    Res.get_res_path("sound/com_stop")
                    )
        self._home.setResume(False)
        self._speaker.speak(action + target + minutes + u"分钟")

        return True, "remind"


class alarm_callback(Callback.Callback):
    def callback(self,
            action=None,
            target=None,
            msg=None, 
            pre_value=None):

        if msg is None:
            return False, None
        alarm_time = parse_time(msg)
        INFO("alarm_time:" + alarm_time)
        if alarm_time is None:
            WARN("invalid alarm time:", msg)
            return False, None

        self._home.setResume(True)
        p = Popen(["at", alarm_time],
                stdin=PIPE,
                stdout=PIPE,
                bufsize=1)
        url = Sound.get_play_request_url(Res.get_res_path("sound/com_bell2"), 6)
        print >>p.stdin, "mpg123 \"" + url + "\""
        print p.communicate("EOF")[0]

        Sound.play(
                    Res.get_res_path("sound/com_stop")
                    )
        self._home.setResume(False)
        self._speaker.speak(action + target + alarm_time)

        return True, "remind"


class task_callback(Callback.Callback):
    def callback(self, cmd, action, msg):
        if action == u"显示" and msg == u"列表":
            threads = self._home._cmd.threads
            info = u"==========\n"
            if len(threads) <= 1: #  当前任务不计入
                info += u"当前无任务"
                info += u"\n=========="
                INFO(info)
                self._home.publish_info(cmd, info)
            else:
                info += u"任务列表:"
                for thread_index in threads:
                    if threads[thread_index][0] == cmd:
                        continue
                    info += u"\n序号：%d 内容：%s" % (thread_index, threads[thread_index][0])
                info += u"\n=========="
                INFO(info)
                self._home.publish_info(cmd, info)
        elif action == u'停止':
            thread_index = cn2dig(msg)
            if thread_index is None or thread_index == '':
                WARN("invaild thread index %s" % (thread_index, ))
                return False, None
            else:
                thread_index = int(thread_index)
            if thread_index in self._home._cmd.threads:
                cmd, thread = self._home._cmd.threads[thread_index]
                thread.stop()
                self._home.publish_info(cmd, u"停止执行任务%d" % (thread_index, ))
                INFO("stop thread: %d with cmd: %s" % (thread_index, cmd))
        return True, True
