#!/usr/bin/env python
# encoding: utf-8

import urllib2
import json
import glob
import types
import httplib
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


class weather_report_callback(Callback.Callback):
    def callback(self, cmd, action, target, msg, pre_value):
        url = 'http://m.weather.com.cn/data/101280101.html'  # Guangzhou
        re = urllib2.urlopen(url).read()
        re = re.decode('UTF-8')
        we = json.loads(re)['weatherinfo']

        info = ""
        info += u'城市：' + we['city'] + "\n"
        info += u'日期：' + we['date_y'] + "\n"
        info += u'week：' + we['week'] + "\n"
        info += u'未来6天天气：' + "\n"
        info += '\t' + we['temp1'] + '\t' + we['weather1'] + '\t' + we['wind1'] + "\n"
        info += '\t' + we['temp2'] + '\t' + we['weather2'] + '\t' + we['wind2'] + "\n"
        info += '\t' + we['temp3'] + '\t' + we['weather3'] + '\t' + we['wind3'] + "\n"
        info += '\t' + we['temp4'] + '\t' + we['weather4'] + '\t' + we['wind4'] + "\n"
        info += '\t' + we['temp5'] + '\t' + we['weather5'] + '\t' + we['wind5'] + "\n"
        info += '\t' + we['temp6'] + '\t' + we['weather6'] + '\t' + we['wind6'] + "\n"
        info += u'穿衣指数: ' + we['index_d'] + "\n"
        info += u'紫外线: ' + we['index_uv']

        self._home.publish_info(cmd, info)

        content = ""
        if msg == u"明天":
            content += u'明天天气：' + ',' + we['temp2'] + ',' + we['weather2'] + '.\n'
        elif msg == u"今天":
            content += u'今天天气：' + ',' + we['temp1'] + ',' + we['weather1'] + '.\n'
        else:
            content += u'今天天气：' + ',' + we['temp1'] + ',' + we['weather1'] + '.\n'
            content += u'明天天气：' + ',' + we['temp2'] + ',' + we['weather2'] + '.\n'
            content += u'后天天气：' + ',' + we['temp3'] + ',' + we['weather3'] + '.\n'
        content += u'穿衣指数：' + we['index_d'] + '\n'

        self._speaker.speak(content.split('\n'), inqueue=True)

        return True, True


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
        if pre_value == "play":
            music_id = "9" # 轻音乐
            if msg in self.__music_table:
                music_id = self.__music_table[msg]
            play = self._context["player"] 
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
        if pre_value == "new":
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
        elif pre_value == "play":
            self._home.setResume(True)

            play = self._context["player"]
            for idx, filepath in enumerate(glob.glob("usr/message/*.mp3")):
                self._speaker.speak(u'第%d条留言' % (idx + 1))
                play(filepath)

            Sound.play(
                        Res.get_res_path("sound/com_stop")
                        )

            self._home.setResume(False)
        elif pre_value == "remove":
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
        if pre_value == "set" or pre_value == "new":
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

        return True, True


class todo_callback(Callback.Callback):
    def callback(self, cmd, action, target, msg, pre_value):
        pass


class alarm_callback(Callback.Callback):
    def callback(self,
            action=None,
            target=None,
            msg=None, 
            pre_value=None):
        if pre_value == "set" or pre_value == "new":
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

        return True, True


class task_callback(Callback.Callback):
    def callback(self, cmd, action, msg, pre_value):
        if pre_value == "show" and msg == u"列表":
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
        elif pre_value == "break":
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
    def callback(self, cmd, action, msg, pre_value):
        if pre_value == "new":
            pass
        elif pre_value == "remove":
            pass
        return True


class switch_callback(Callback.Callback):
    def callback(self, cmd, action, target, msg, pre_value):
        if pre_value == "show":
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
    def callback(self, cmd, action, target, msg, pre_value):
        ip = self._home._switch.ip_for_name(target)
        if pre_value == "on":
            return True, True
        elif pre_value == "off":
            return True, True
        elif pre_value == "show" and msg == u"状态":
            state = self._home._switch.show_state(ip)
            if state is None:
                self._home.publish_info(cmd, u"内部错误")
                return False
            info = u"名称:" \
                   + target \
                   + u" 状态:" \
                   + state
            self._home.publish_info(cmd, info)
            return True, state
        else:
            return False
