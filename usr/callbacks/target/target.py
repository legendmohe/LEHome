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
        if action == u"新增":
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
        elif action == u"删除":
            filelist = glob.glob("usr/message/*.mp3")
            for f in filelist:
                os.remove(f)
                INFO("remove:%s" % (f, ))
            Sound.play(
                        Res.get_res_path("sound/com_trash")
                        )
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

        return True, pre_value


class task_callback(Callback.Callback):
    def callback(self, cmd, action, msg):
        if action == u"显示" and msg == u"列表":
            threads = self._home._cmd.threads
            info = u""
            if len(threads) <= 1: #  当前任务不计入
                info += u"当前无任务"
                INFO(info)
                self._home.publish_info(cmd, info)
            else:
                info += u"任务列表:"
                for thread_index in threads:
                    if threads[thread_index][0] == cmd:
                        continue
                    info += u"\n  序号：%d 内容：%s" % (thread_index, threads[thread_index][0])
                INFO(info)
                self._home.publish_info(cmd, info)
        elif action == u'停止' or action == u"结束":
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


class script_callback(Callback.Callback):
    def callback(self, cmd, action, msg):
        if action == u"新增":
            pass
        elif action == u"删除":
            pass
        return True


class switch_callback(Callback.Callback):
    def callback(self, cmd, action, target, msg):
        if msg == u"列表" or msg == u"状态":
            states = self._home._switch.list_state()
            if states is None:
                self._home.publish_info(cmd, u"内部错误")
            elif len(states) == 0:
                self._home.publish_info(cmd, target + u"列表为空")
            else:
                info = target + u"列表:"
                for switch_ip in states:
                    switch_name = self._home._switch.name_for_ip(switch_ip)
                    info += u"\n  名称:" \
                            + switch_name \
                            + u" 状态:" \
                            + states[switch_ip]["state"]
                self._home.publish_info(cmd, info)
        return True


class lamp_callback(Callback.Callback):
    def callback(self, cmd, action, target, msg):
        ip = self._home._switch.ip_for_name(target)
        if action == u"打开":
            state = self._home._switch.show_state(ip)
            if state is None:
                self._home.publish_info(cmd, u"内部错误")
            elif state == "close":
                res = self._home._switch.send_open(ip)
                if res is None:
                    self._home.publish_info(cmd, u"内部错误")
                elif res == "open":
                    self._home.publish_info(cmd, u"打开" + target)
                else:
                    self._home.publish_info(cmd, u"打开" + target + u"失败")
            return True, True
        elif action == u"关闭":
            state = self._home._switch.show_state(ip)
            if state is None:
                self._home.publish_info(cmd, u"内部错误")
            elif state == "open":
                res = self._home._switch.send_close(ip)
                if res is None:
                    self._home.publish_info(cmd, u"内部错误")
                elif res == "close":
                    self._home.publish_info(cmd, u"关闭" + target)
                else:
                    self._home.publish_info(cmd, u"关闭" + target + u"失败")
            return True, True
        elif msg == u"状态":
            state = self._home._switch.show_state(ip)
            if state is None:
                self._home.publish_info(cmd, u"内部错误")
                return False
            info = u"\n  名称:" \
                   + target \
                   + u" 状态:" \
                   + state
            self._home.publish_info(cmd, info)
            return True, state
        else:
            return False
