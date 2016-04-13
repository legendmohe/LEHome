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


import urllib
import urllib2
import json
import pickle
import glob
import httplib
import os
import io
import re
import threading
import errno
import time
from datetime import datetime

from bs4 import BeautifulSoup

from lib.command.runtime import UserInput
from util.Res import Res
from util import Util
from lib.sound import Sound
from util.log import *
from lib.model import Callback
from lib.helper.SensorHelper import SensorHelper


class target_callback(Callback.Callback):
    def callback(self,
            action=None,
            target=None,
            msg=None, 
            pre_value=None):
        INFO("* target callback: %s, message: %s pre_value: %s" %(target, msg, pre_value))
        return True, "pass"


class weather_report_callback(Callback.Callback):

    BAIDU_WEATHER_AK = "7P5ZCG6WTAGWr5TuURBgndRH"

    def callback(self, cmd, action, target, msg, pre_value):
        if pre_value == 'show' or pre_value == 'get':
            if pre_value == 'show':
                self._home.publish_msg(cmd, u'正在获取天气讯息...')
            try:
                if Util.empty_str(msg):
                    city_name = u'广州'  # Guangzhou
                else:
                    city_name = msg
                url = "http://api.map.baidu.com/telematics/v3/weather?"
                url += urllib.urlencode({
                    'location': city_name.encode('utf8'),
                    'output': "json",
                    'ak': weather_report_callback.BAIDU_WEATHER_AK
                    })
                ret = urllib2.urlopen(url, timeout=10).read()
                data = json.loads(ret)
                INFO("weather request: %s" % url)
                INFO("weather data: %s" % data)
                if data["error"] != 0:
                    self._home.publish_msg(cmd, u"获取天气信息失败")
                    return True

                content = []
                spk_content = []
                content.append(u"日期：" + data["date"])
                spk_content.append(u"日期：" + data["date"])

                w_results = data["results"]
                for city in w_results:
                    spk_content.append(u"PM25：" + city["pm25"])
                    today_data = city["weather_data"][0]
                    spk_content.append(u"    %s, %s" % (today_data["weather"], today_data["wind"]))
                    spk_content.append(u"    %s" % (today_data["temperature"],))

                    content.append(u"城市：" + city["currentCity"])
                    content.append(u"PM25：" + city["pm25"])
                    content.append(u"小提示:")
                    for w_index in city["index"]:
                        if w_index["title"] in [u"穿衣", u"紫外线强度"]:
                            content.append(u"        " + w_index["des"])
                    content.append(u"==========")
                    for w_data in city["weather_data"]:
                        content.append(u"" + w_data["date"])
                        content.append(u"    %s, %s" % (w_data["weather"], w_data["wind"]))
                        content.append(u"    %s" % (w_data["temperature"],))
                        # content.append(u"") 
                content = u"\n".join(content)
                if pre_value == 'show':
                    self._home.publish_msg(cmd, content)
                    self._speaker.speak(spk_content)
                return True, data
            except Exception, ex:
                ERROR(ex)
                ERROR("weather target faild.")
                self._home.publish_msg(cmd, u"获取天气信息失败")
                return True
        return True


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
            play = self._global_context["player"] 
            httpConnection = httplib.HTTPConnection('douban.fm')
            httpConnection.request('GET', '/j/mine/playlist?type=n&channel=' + music_id)
            song = json.loads(httpConnection.getresponse().read())['song']
            play(song[0]['url'], inqueue=False)
        return True, "pass"


class qqfm_callback(Callback.Callback):

    base_url = 'http://' + Res.get('qqfm/server')
    channel_url = base_url + '/list'
    next_url = base_url + '/next'
    pause_url = base_url + '/pause'
    cur_url = base_url + '/current'

    def init_channcels(self):
        self._fm_state = 0
        try:
            INFO("init qqfm:" + qqfm_callback.channel_url)
            channels = urllib2.urlopen(qqfm_callback.channel_url, timeout=5).read()
            self.channels = [channel.decode("utf-8") for channel in channels.split('\n')]
        except Exception, ex:
            ERROR("qqfm init error.")
            ERROR(ex)
            self._home.publish_msg("init qqfm", u"连接失败")
            self.channels = []

    def get_current_song(self):
        try:
            rep = urllib2.urlopen(qqfm_callback.cur_url, timeout=5).read()
            DEBUG("get current song:" + rep)
            data = json.loads(rep)
            if len(data) == 0:
                return None
            return data
        except Exception, ex:
            ERROR("get current song error.")
            ERROR(ex)
            return None

    def callback(self, cmd, action, target, msg, pre_value):
        try:
            if not hasattr(self, "channels") or len(self.channels) == 0:
                self.init_channcels()
            if len(self.channels) == 0:
                self._home.publish_msg(cmd, u"电台列表初始化失败")
                return True
            if pre_value == "show":
                if len(self.channels) == 0:
                    self._home.publish_msg(cmd, u"无电台列表")
                else:
                    info = ""
                    song = self.get_current_song()
                    if song is not None:
                        info += u"正在播放:\n"
                        info += u"  频道:%s\n" % song["channel"]
                        info += u"  歌曲:%s\n" % song["name"]
                        info += u"  歌手:%s\n" % song["singer"]
                    info += u"电台列表:\n"
                    info += u", ".join(self.channels)
                    self._home.publish_msg(cmd, info)
            elif pre_value == "play" \
                    or pre_value == "run"\
                    or pre_value == "on":
                if len(self.channels) == 0:
                    self._home.publish_msg(cmd, u"无电台列表")
                else:
                    if msg is None:
                        msg = ""
                    play_url = qqfm_callback.next_url \
                            + "?" + urllib.urlencode(
                                        {'type':msg.encode('utf-8')}
                                    )
                    INFO("qqfm playing:%s" % (play_url,))
                    rep = urllib2.urlopen(play_url, timeout=5).read()
                    INFO("qqfm playing state: " + rep)
                    self._home.publish_msg(cmd, u"正在播放:" + rep.decode("utf-8"))
                    self._fm_state = 1
            elif pre_value == "break" or pre_value == "off":
                rep = urllib2.urlopen(qqfm_callback.pause_url, timeout=3).read().decode("utf-8")
                INFO("qqfm playing state: " + rep)
                if rep == "pause":
                    self._fm_state = 0
                if self._fm_state == 1:
                    self._home.publish_msg(cmd, u"停止播放")
        except Exception, ex:
            ERROR("qqfm error.")
            ERROR(ex)
            self._home.publish_msg(cmd, u"播放失败")
        return True


class newsfm_callback(Callback.Callback):

    base_url = 'http://ctt.rgd.com.cn:8000'
    channel_url = base_url + '/fm914'

    def callback(self, cmd, action, target, msg, pre_value):
        if pre_value == "play":
            play = self._global_context["player"]
            play(newsfm_callback.channel_url)
            self._home.publish_msg(cmd, u"正在播放" + target)
        return True


class message_callback(Callback.Callback):
    def callback(
            self,
            cmd,
            action=None,
            target=None,
            msg=None, 
            pre_value=None):
        if pre_value == "new":
            path = "usr/message/"
            try:
                os.makedirs(path)
            except OSError as exc:
                if exc.errno == errno.EEXIST and os.path.isdir(path):
                    pass
                else:
                    ERROR(exc)
                    return False

            self._home.setResume(True)
            filepath = path + datetime.now().strftime("%m_%d_%H_%M") + ".mp3"
            Sound.notice(Res.get_res_path("sound/com_stop"))
            record = self._global_context["recorder"]
            self._home.publish_msg(cmd, u"录音开始...")
            record(filepath)
            self._home.publish_msg(cmd, u"录音结束")
            self._home.setResume(False)
        elif pre_value == "play" or pre_value == "show":
            messages = glob.glob("usr/message/*.*")
            messages.sort(key=os.path.getctime)
            if msg == u"最新" or msg == u"最后":
                msg = "1"
            if msg is not None and len(messages) > 0:
                digits = re.findall('\d+', msg)
                if len(digits) > 0:
                    messages = messages[-int(digits[0]):]
            if pre_value == "play":
                play = self._global_context["player"]
                for idx, filepath in enumerate(messages):
                    INFO(u'第%d条留言:%s' % (idx + 1, filepath))
                    play(Res.get_res_path("sound/com_stop"))
                    play(filepath, channel="notice")
            elif pre_value == "show":
                info = []
                for idx, filepath in enumerate(messages):
                    filename = os.path.basename(filepath).split('.')[0]
                    info.append(u"  第%d条: %s" % (idx + 1, filename))
                info.insert(0, u"[你有%d条留言]" % (len(info),))
                INFO(u"\n".join(info))
                self._home.publish_msg(cmd, u"\n".join(info))
        elif pre_value == "remove":
            filelist = glob.glob("usr/message/*.*")
            for f in filelist:
                os.remove(f)
                INFO("remove:%s" % (f, ))
            Sound.notice(
                        Res.get_res_path("sound/com_trash")
                        )
            self._home.publish_msg(cmd, u"删除成功")
        return True


class record_callback(Callback.Callback):
    def callback(self,
            cmd,
            action=None,
            target=None,
            msg=None, 
            pre_value=None):
        
        if pre_value == "new":
            path = "usr/memo/"
            try:
                os.makedirs(path)
            except OSError as exc:
                if exc.errno == errno.EEXIST and os.path.isdir(path):
                    pass
                else:
                    ERROR(exc)
                    self._home.publish_msg(cmd, u"录音错误")
                    return False

            self._home.setResume(True)
            filepath = path + datetime.now().strftime("%m_%d_%H_%M") + ".mp3"
            record = self._global_context["recorder"]
            self._home.publish_msg(cmd, u"录音开始...")
            record(filepath)
            self._home.publish_msg(cmd, u"录音结束")
            Sound.notice(
                        Res.get_res_path("sound/com_stop")
                        )
            self._home.setResume(False)
        return True

class bell_callback(Callback.Callback):
    def callback(self,
            action=None,
            target=None,
            msg=None, 
            pre_value=None):
        if pre_value == "play":
            if msg is None or not msg.endswith(u"次"):
                count = 5
            else:
                count = int(Util.cn2dig(msg[:-1]))
            self._home.setResume(True)
            play = self._global_context["player"]
            play(Res.get_res_path("sound/com_bell"), channel='notice', loop=count)
            self._home.setResume(False)
        return True


class warning_bell_callback(Callback.Callback):
    def callback(self,
            action=None,
            target=None,
            msg=None, 
            pre_value=None):
        if pre_value == "play":
            if msg is None or not msg.endswith(u"次"):
                count = 1
            else:
                count = int(Util.cn2dig(msg[:-1]))
            self._home.setResume(True)
            play = self._global_context["player"]
            play(Res.get_res_path("sound/com_warn"), channel='notice', loop=count)
            self._home.setResume(False)
        return True


class alarm_callback(Callback.Callback):
    def callback(self,
            cmd,
            action=None,
            target=None,
            msg=None, 
            pre_value=None):
        if pre_value == "new" or pre_value == "set":
            if msg is None:
                self._home.publish_msg(cmd, u"时间格式错误")
                return False, None

            if msg.endswith(u'点') or \
                msg.endswith(u'分'):
                t = Util.gap_for_timestring(msg)
            else:
                self._home.publish_msg(cmd, u"时间格式错误")
                return False
            if t is None:
                self._home.publish_msg(cmd, u"时间格式错误")
                return False, None

            INFO("alarm wait for %d sec" % (t, ))
            self._home.publish_msg(cmd, action + target + msg)

            threading.current_thread().waitUtil(t)
            if threading.current_thread().stopped():
                return False
            self._home.setResume(True)
            count = 7
            Sound.notice( Res.get_res_path("sound/com_bell") , True, count)
            self._home.setResume(False)
            return True


class todo_callback(Callback.Callback):

    todo_path = "data/todo.pcl"

    def __init__(self):
        super(todo_callback, self).__init__()
        self._lock = threading.Lock()
        self.load_todos()

    def load_todos(self):
        with self._lock:
	    self.todos = []
            try:
                with open(todo_callback.todo_path, "rb") as f:
                    self.todos = pickle.load(f)
            except:
                INFO("empty todo list.")
        return self.todos

    def save_todos(self):
        with self._lock:
            try:
                with open(todo_callback.todo_path, "wb") as f:
                    pickle.dump(self.todos, f, True)
            except Exception, e:
                ERROR(e)
                ERROR("invaild save todo path:%s", todo_callback.todo_path)

    def todo_at_index(self, index):
        if index < 0 or index >= len(self.todos):
            ERROR("invaild todo index.")
            return NULL
        else:
            return self.todos[index]

    def add_todo(self, content):
        if content is None or len(content) == 0:
            ERROR("empty todo content.")
            return False
        self.todos.append(content)
        return True

    def remove_todo_at_index(self, index):
        if index < 0 or index >= len(self.todos):
            ERROR("invaild todo index.")
            return False
        else:
            del self.todos[index]
            self.save_todos()
            return True

    def callback(self, cmd, action, target, msg, pre_value):
        if pre_value == "show":
            info = ""
            # self.load_todos()
            for index, todo in enumerate(self.todos):
                info += u"序号: %d\n    内容:%s\n"  \
                        % (index, self.todos[index])
            if len(info) == 0:
                info = u"当前无" + target
            else:
                info = info[:-1]
            self._home.publish_msg(cmd, info)
        elif pre_value == "new":
            if Util.empty_str(msg):
                cancel_flag = u"取消"
                finish_flag = u"完成"
                self._home.publish_msg(
                    cmd
                    , u"请输入内容, 输入\"%s\"或\"%s\"结束:" % (finish_flag, cancel_flag)
                    , cmd_type="input"
                )
                msg = UserInput(self._home).waitForInput(
                                                        finish=finish_flag,
                                                        cancel=cancel_flag)
            if msg is None  \
                    or not self.add_todo(msg):
                self._home.publish_msg(cmd, u"新建失败")
            else:
                self._home.publish_msg(cmd, u"新建成功")
                self.save_todos()
        elif pre_value == "remove":
            index = Util.cn2dig(msg)
            if not index is None:
                if self.remove_todo_at_index(int(index)):
                    INFO("remove todo: " + msg)
                    self._home.publish_msg(cmd
                            , u"删除" + target + ": " + msg)
                else:
                    self._home.publish_msg(cmd, u"无此编号:" + index)
            else:
                self._home.publish_msg(cmd, u"编号出错")
        return True


class task_callback(Callback.Callback):

    task_path = "data/task.pcl"

    def __init__(self):
        super(task_callback, self).__init__()
        self._lock = threading.Lock()
        self.load_tasks()

    def load_tasks(self):
        with self._lock:
            self._tasks = {}
            try:
                with open(task_callback.task_path, "rb") as f:
                    self._tasks = pickle.load(f)
            except:
                INFO("empty suspended task list.")
        return self._tasks

    def save_tasks(self):
        try:
            with open(task_callback.task_path, "wb") as f:
                pickle.dump(self._tasks, f, True)
        except Exception, e:
            ERROR(e)
            ERROR("invaild save tasks path:%s", task_callback.task_path)

    def suspend_task(self, index):
        with self._lock:
            cmd, thread = self._home.runtime.threads[index]
            thread.stop()
            while index in self._tasks:
                index += 1
            self._tasks[index] = cmd
            self.save_tasks()

    def resume_task(self, index):
        with self._lock:
            try:
                cmd = self._tasks[index]
            except IndexError:
                cmd = None
            if cmd is None:
                ERROR("invaild resume_task index:%d" % index)
                return False
            else:
                del self._tasks[index]
                self.save_tasks()
                self._home.runtime._fsm.put_cmd_into_parse_stream(cmd)
                return True

    def show_current_task(self, cmd):
        info = u"运行中:\n" + u"="*20
        threads = self._home.runtime.threads
        for idx in threads:
            if threads[idx][0] == cmd:
                continue
            info += u"\n  序号：%d 内容：%s" % (idx, threads[idx][0])
        info += u"\n\n暂停中:\n" + u"="*20
        for idx in self._tasks:
            info += u"\n  序号：%d 内容：%s" % (idx, self._tasks[idx])
        INFO(u"\n" + info)
        self._home.publish_msg(cmd, info)

    def callback(self, cmd, action, msg, pre_value):
        if pre_value == "show":
            threads = self._home.runtime.threads
            info = u""
            if len(threads) <= 1 and len(self._tasks) == 0: #  当前任务不计入
                info += u"当前无任务"
                INFO(info)
                self._home.publish_msg(cmd, info)
            else:
                if msg is None or len(msg) == 0:
                    self.show_current_task(cmd)
                else:
                    thread_index = Util.cn2dig(msg)
                    if thread_index is None or thread_index == '':
                        WARN("invaild thread index %s" % (msg, ))
                        self._home.publish_msg(cmd, u"任务序号格式错误:" + msg)
                    else:
                        thread_index = int(thread_index)
                        if thread_index in threads:
                            info += u"内容：%s" % (threads[thread_index][0], )
                            INFO(info)
                            self._home.publish_msg(cmd, info)
                        else:
                            WARN("invaild thread index %s" % (msg, ))
                            self._home.publish_msg(cmd, u"无此任务序号:%d" % thread_index)
        elif pre_value == "break":
            thread_index = Util.cn2dig(msg)
            if thread_index is None or thread_index == '':
                WARN("invaild thread index %s" % (msg, ))
                self._home.publish_msg(cmd, u"无任务序号:" + msg)
                return False, None
            else:
                thread_index = int(thread_index)
            if thread_index in self._home.runtime.threads:
                cmd, thread = self._home.runtime.threads[thread_index]
                thread.stop()
                self._home.publish_msg(cmd, u"停止执行任务%d" % (thread_index, ))
                INFO("stop thread: %d with cmd: %s" % (thread_index, cmd))
                # show current task
                # self.show_current_task(cmd)
            else:
                WARN("invaild thread index %s" % (thread_index, ))
                self._home.publish_msg(cmd, u"无此任务序号:%d" % thread_index)
        elif pre_value == "suspend":
            thread_index = Util.cn2dig(msg)
            if thread_index is None or thread_index == '':
                WARN("invaild thread index %s" % (msg, ))
                self._home.publish_msg(cmd, u"无任务序号:" + msg)
                return False, None
            else:
                thread_index = int(thread_index)
            if thread_index in self._home.runtime.threads:
                self.suspend_task(thread_index)
                self._home.publish_msg(cmd, u"暂停执行任务%d" % (thread_index, ))
                INFO("suspend thread: %d with cmd: %s" % (thread_index, cmd))
                # show current task
                # self.show_current_task(cmd)
            else:
                WARN("invaild thread index %s" % (thread_index, ))
                self._home.publish_msg(cmd, u"无此任务序号:%d" % thread_index)
        elif pre_value == "resume":
            task_index = Util.cn2dig(msg)
            if task_index is None or task_index == '':
                WARN("invaild thread index %s" % (msg, ))
                self._home.publish_msg(cmd, u"无任务序号:" + msg)
                return False, None
            else:
                task_index = int(task_index)
            if self.resume_task(task_index) is True:
                self._home.publish_msg(cmd, u"恢复执行任务%d" % (task_index, ))
                INFO("resume thread: %d with cmd: %s" % (task_index, cmd))
                # show current task
                # self.show_current_task(cmd)
            else:
                self._home.publish_msg(cmd, u"恢复执行任务失败:%d" % (task_index, ))
                INFO("resume thread faild: %d with cmd: %s" % (task_index, cmd))
        return True, True


class script_callback(Callback.Callback):

    script_path = "data/scripts.pcl"

    def __init__(self):
        super(script_callback, self).__init__()
        self._lock = threading.Lock()
        self.load_scripts()

    def load_scripts(self):
        with self._lock:
	    self.scripts = {}
            try:
                with io.open(script_callback.script_path,
                                "r",
                                encoding="utf-8") as f:
                    # self.scripts = pickle.load(f)
                    for line in f.readlines():
                        script_token = line.split()
                        if(len(script_token) == 2):
                            self.scripts[script_token[0]] = script_token[1]
            except:
                INFO("empty script list.")
        return self.scripts

    def save_scripts(self):
        with self._lock:
            try:
                with io.open(script_callback.script_path,
                        "w", 
                        encoding="utf-8") as f:
                    for key in self.scripts:
                        f.write("%s %s\n" % (key, self.scripts[key]))
                    # pickle.dump(self.scripts, f, True)
            except Exception, e:
                ERROR(e)
                ERROR("invaild save script path:%s", script_callback.script_path)

    def script_by_name(self, name):
        if name in self.scripts:
            return self.scripts[name]
        return None

    def add_script(self, name, content):
        if name is None or len(name) == 0:
            ERROR("empty script name.")
            return False
        if content is None or len(content) == 0:
            ERROR("empty script content.")
            return False
        self.scripts[name] = content
        return True

    def remove_script_by_name(self, name):
        if name in self.scripts:
            del self.scripts[name]
            self.save_scripts()
            return True
        return False

    def run_script(self, name):
        script = self.script_by_name(name)
        if script is None or len(script) == 0:
            ERROR("empty script content or invaild script name.")
            return False
        else:
            self._home.parse_cmd(script, persist=False)
            return True

    def callback(self, cmd, action, target, msg, pre_value):
        if pre_value == "show":
            info = ""
            # self.load_scripts()
            if msg is None or len(msg) == 0:
                for script_name in self.scripts:
                    info += u"名称: " + script_name  \
                            + u"\n    内容: " + self.scripts[script_name]  \
                            + "\n"
                if len(info) == 0:
                    info = u"当前无" + target
                else:
                    info = info[:-1]
            else:
                if msg in self.scripts:
                    info = u'内容：' + self.scripts[msg]
                else:
                    info = u"无此脚本：" + msg
            self._home.publish_msg(cmd, info)
            INFO(info)
        else:
            if msg is None or len(msg) == 0:
                self._home.publish_msg(cmd, u"缺少脚本名称")
                return False
            script_name = msg
            if pre_value == "new":
                cancel_flag = u"取消"
                finish_flag = u"完成"
                self._home.publish_msg(cmd
                        , u"脚本名称: " + script_name  \
                        + u"\n请输入脚本内容, 输入\"" + cancel_flag  \
                        + u"\"或\"" + finish_flag + u"\"结束..."
                        , cmd_type="input")
                userinput = UserInput(self._home).waitForInput(
                                                            finish=finish_flag,
                                                            cancel=cancel_flag)
                if userinput is None  \
                        or not self.add_script(script_name, userinput):
                    self._home.publish_msg(cmd, u"新建脚本失败")
                else:
                    self._home.publish_msg(cmd, u"成功新建脚本")
                    self.save_scripts()
            elif pre_value == "remove":
                if self.remove_script_by_name(script_name):
                    INFO("remove script: " + script_name)
                    self._home.publish_msg(cmd, u"删除脚本:" + script_name)
            elif pre_value == "run":
                if self.run_script(script_name) is False:
                    self._home.publish_msg(cmd, u"无效脚本")
                else:
                    self._home.publish_msg(cmd,
                                            u"执行脚本:" + script_name,
                                            cmd_type="toast")
        return True


class var_callback(Callback.Callback):

    var_path = "data/vars.pcl"

    def __init__(self):
        super(var_callback, self).__init__()
        self._lock = threading.Lock()

    def init(self):
        self.load_vars()

    def load_vars(self):
        with self._lock:
	    self.vars = {}
            try:
                with open(var_callback.var_path, "rb") as f:
                    self.vars = pickle.load(f)
            except Exception, e:
                ERROR(e)
                INFO("empty var list.")
        return self.vars

    def save_vars(self):
        with self._lock:
            try:
                with open(var_callback.var_path, "wb") as f:
                    pickle.dump(self.vars, f, True)
            except Exception, e:
                ERROR(e)
                ERROR("invaild save var path:%s", var_callback.var_path)

    def var_by_name(self, name):
        with self._lock:
            if name in self.vars:
                return self.vars[name]
        return None

    def add_var(self, name, content):
        if Util.empty_str(name):
            ERROR("empty var name.")
            return False
        if content is None:
            ERROR("empty var content.")
            return False
        self.vars[name] = content
        return True

    def remove_var_by_name(self, name):
        with self._lock:
            if name in self.vars:
                del self.vars[name]
                self.save_vars()
                return True
            return False

    def callback(self, cmd, action, msg, pre_value):
        if pre_value == "show":
            info = ""
            # bugs
            # self.load_vars()
            if Util.empty_str(msg):
                for var_name in self.vars:
                    info += u"名称: " + var_name  \
                            + u"\n    内容: " + unicode(self.vars[var_name])  \
                            + "\n"
                if len(info) == 0:
                    info = u"当前无变量列表"
                else:
                    info = info[:-1]
            else:
                if msg not in self.vars:
                    info = u"无变量:" + msg
                else:
                    info = u"内容为:" + unicode(self.vars[msg])
            self._home.publish_msg(cmd, info)
            INFO(info)
        elif pre_value == "get":
            # self.load_vars()
            if Util.empty_str(msg):
                self._home.publish_msg(cmd, u"缺少变量名称")
                return False
            # import pdb; pdb.set_trace()
            #return True, self.var_by_name(msg)
            if msg not in self.vars:
                self._home.publish_msg(cmd, u"无变量:" + msg)
                return False
            else:
                # INFO(u'变量:' + unicode(self.vars[msg]))
                return True, self.vars[msg]
        else:
            if Util.empty_str(msg):
                self._home.publish_msg(cmd, u"缺少变量名称")
                return False
            if pre_value == "new" or pre_value == "set":
                spos = msg.find(u'为')
                if spos != -1:
                    var_name = msg[:spos]
                    var_value = msg[spos + 1:]
                    parse_value = Util.var_parse_value(var_value)
                    if parse_value is None:
                        ERROR("var_parse_value error.")
                        return False
                elif pre_value != None:
                    var_name = msg
                    parse_value = pre_value
                else:
                    info = u"格式错误"
                    ERROR(info)
                    self._home.publish_msg(cmd, info)
                    return False
                if not self.add_var(var_name, parse_value):
                    self._home.publish_msg(cmd, u"新建变量失败")
                else:
                    if pre_value == "new":
                        self._home.publish_msg(cmd,
                                u"成功新建变量:" + var_name)
                    self.save_vars()
            elif pre_value == "remove":
                var_name = msg
                if self.remove_var_by_name(var_name):
                    INFO("remove var: " + var_name)
                    self._home.publish_msg(cmd, u"删除变量:" + var_name)
                else:
                    self._home.publish_msg(cmd, u"删除变量失败:" + var_name)
        return True


class switch_callback(Callback.Callback):
    def callback(self, cmd, action, target, msg, pre_value):
        if pre_value == "show":
            switchs = self._home._switch.switchs
            if len(switchs) == 0:
                self._home.publish_msg(cmd, target + u"列表为空")
            else:
                info = target + u"列表:"
                for switch_ip in switchs:
                    infos = self._home._switch.show_info(switch_ip)
                    readable_info = self._home._switch.readable_info(infos)
                    if Util.empty_str(readable_info) is True:
                        readable_info = u"未知"
                    switch_name = self._home._switch.name_for_ip(switch_ip)
                    if Util.empty_str(switch_name)is True:
                        switch_name = u"未知"
                    info += u"\n  名称:" \
                            + switch_name \
                            + u" 状态:" \
                            + self._home._switch.show_state(switch_ip) \
                            + u"\n  " \
                            + readable_info
                self._home.publish_msg(cmd, info)
        return True


class sensor_callback(Callback.Callback):
    def callback(self, cmd, action, target, msg, pre_value):
        if pre_value == "show":
            places = self._home._sensor.get_places()
            if places is None:
                self._home.publish_msg(cmd, u"内部错误")
            elif len(places) == 0:
                self._home.publish_msg(cmd, target + u"列表为空")
            else:
                info = target + u"列表:"
                for place in places:
                    addr = self._home._sensor.addr_for_place(place)
                    state = self._home._sensor.get_all(addr)
                    info += u"\n  名称:" \
                            + place \
                            + u"\n  状态:" \
                            + self._home._sensor.readable(state, SensorHelper.TYPE_ALL)
                INFO(info)
                self._home.publish_msg(cmd, info)
        return True


class normal_switch_callback(Callback.Callback):
    def callback(self, cmd, action, target, msg, pre_value):
        ip = self._home._switch.ip_for_name(target)
        if pre_value == "on":
            return True
        elif pre_value == "off":
            return True
        elif pre_value == "show" or pre_value == "get" and msg == u"状态":
            state = self._home._switch.show_state(ip)
            if state is None:
                self._home.publish_msg(cmd, u"内部错误")
                return False
            infos = self._home._switch.show_info(ip)
            readable_info = self._home._switch.readable_info(infos)
            info = u"名称:" \
                   + target \
                   + u" 状态:" \
                   + state  \
                   + u"\n  " \
                   + readable_info
            if pre_value == "show":
                self._home.publish_msg(cmd, info)
            return True, state
        else:
            return False


class normal_ril_callback(Callback.Callback):

    ON = "\x40"
    OFF = "\x41"

    def __init__(self):
        super(normal_ril_callback, self).__init__()
        self._ac = {"status":"off"}

    def callback(self, cmd, action, target, msg, pre_value):
        if pre_value != None and len(pre_value) != 0:
            res = None
            if pre_value == "on":
                if self._ac["status"] == "off":
                    res = self._home._ril.send_cmd(normal_ril_callback.ON)
                    if res == None:
                        self._home.publish_msg(cmd, u"%s打开失败" % target)
                    else:
                        self._home.publish_msg(cmd, u"%s打开成功" % target)
                        self._ac["status"] = "on"
                else:
                    self._home.publish_msg(cmd, u"%s已经打开" % target)
            elif pre_value == "off":
                if self._ac["status"] == "on":
                    res = self._home._ril.send_cmd(normal_ril_callback.OFF)
                    if res == None:
                        self._home.publish_msg(cmd, u"%s关闭失败" % target)
                    else:
                        self._home.publish_msg(cmd, u"%s关闭成功" % target)
                        self._ac["status"] = "off"
                else:
                    self._home.publish_msg(cmd, u"%s已经关闭" % target)
            elif pre_value == "show":
                if self._ac["status"] == "on":
                    self._home.publish_msg(cmd, u"%s已打开" % target)
                else:
                    self._home.publish_msg(cmd, u"%s已关闭" % target)
            elif pre_value == "get":
                if self._ac["status"] == "on":
                    return True, "on"
                else:
                    return True, "off"
        return True, True


class normal_sensor_callback(Callback.Callback):
    def callback(self, cmd, action, target, msg, pre_value):
        pass

class normal_person_callback(Callback.Callback):
    def callback(self, cmd, action, target, msg, pre_value):
        if pre_value == "show" or pre_value == "get":
            device_ip = self._home._ping.device_ip_for_name(target)
            if device_ip is None:
                self._home.publish_msg(cmd, u"无此目标：" + target)
                return False
            if msg.startswith(u'在'):
                here = True
                msg = msg[1:]
            elif msg.startswith(u'不在'):
                here = False
                msg = msg[2:]
            else:
                self._home.publish_msg(cmd, u"格式错误：" + cmd)
                return False

            res = self._home._ping.online(device_ip)
            if res is None:
                INFO(u'无法获取位置：' + cmd)
                self._home.publish_msg(cmd, u"无法获取位置信息：" + msg)
                return False
            else:
                status = u"在" if res else u"不在"
                info = target + status + msg
                if here is False:
                    res = not res
            if pre_value == "show":
                self._home.publish_msg(cmd, info)
            return True, res
        else:
            return True


class speech_callback(Callback.Callback):
    def callback(self, cmd, action, target, msg, pre_value):
        if pre_value == "play":
            if Util.empty_str(msg):
                cancel_flag = u"取消"
                finish_flag = u"完成"
                self._home.publish_msg(cmd
                        , u"请输入内容, 输入\"" + cancel_flag  \
                        + u"\"或\"" + finish_flag + u"\"结束..."
                        , cmd_type="input")
                userinput = UserInput(self._home).waitForInput(
                                                            finish=finish_flag,
                                                            cancel=cancel_flag)
                if userinput is None:
                    WARN("speech content is None.")
                    self._home.publish_msg(cmd, u"语音内容为空")
                    return True
                else:
                    self._speaker.speak(userinput)
                    self._home.publish_msg(cmd, u"播放语音:" + userinput)
            else:
                self._speaker.speak(msg)
                self._home.publish_msg(cmd, u"播放语音:" + msg)
        return True


class bus_callback(Callback.Callback):
    REQUEST_URL = "http://gzbusnow.sinaapp.com/index.php?"
    REQUEST_TIMEOUT = 5

    def _request_info(self, msg):
        url = bus_callback.REQUEST_URL + \
                urllib.urlencode({
                    'keyword': msg.encode('utf8'),
                    'a': 'query',
                    'c': 'busrunningv2'
                    })
        try:
            INFO("start fetching bus info:%s" % msg)
            rep = urllib2.urlopen(
                    url,
                    timeout=bus_callback.REQUEST_TIMEOUT) \
                .read()
            INFO("got bus info:%d" % len(rep))
            return rep
        except urllib2.URLError, e:
            ERROR(e)
            return None

    def _parse_info(self, rep):
        res = []
        soup = BeautifulSoup(rep)
        try:
            for status in soup.find_all(class_='bus_direction'):
                current = {
                        'status': unicode(status.string).strip(),
                        'nodes': []}
                # WTF?!
                begin_node = status.next_sibling.next_sibling.table
                for child in begin_node.children:
                    if type(child) != type(begin_node):
                        continue
                    node = {}
                    if child.get('class') is None:
                        node['in'] = False
                    else:
                        node['in'] = True
                    # WTF?!
                    node['name'] = unicode(child.contents[3].contents[0].string.strip())
                    current['nodes'].append(node)
                res.append(current)
            # import pdb; pdb.set_trace()
        except Exception, e:
            ERROR(e)
        INFO("parse bus info:%d" % len(res))
        return res

    def _bus_info(self, bus_number):
        info = self._request_info(bus_number)
        if info is None:
            return None
        else:
            parse_res = self._parse_info(info)
            if parse_res is None or len(parse_res) == 0:
                return u""
            return parse_res

    def _readable_info(self, info):
        res = ""
        for direction in info:
            res += direction['status'] + u'\n'
            for node in direction['nodes']:
                line = u'|' if node['in'] is False else u'*'
                line += u" %s" % node['name']
                res += line + u'\n'
            res += u'\n'
        return res[:-2]

    def callback(self, cmd, action, target, msg, pre_value):
        if pre_value == "show" or pre_value == "get":
            if msg is None or len(msg) == 0:
                self._home.publish_msg(cmd, u"请输入公交线路名称")
                return True, None
            self._home.publish_msg(cmd, u"正在查询...")
            info = self._bus_info(msg)
            if info is None:
                self._home.publish_msg(cmd, u"公交信息服务连接失败")
                return True, None
            elif info == u"":
                self._home.publish_msg(cmd, u"请输入正确的公交线路名称")
                return True, None
            else:
                readable_info = self._readable_info(info)
                INFO(readable_info)
                self._home.publish_msg(cmd, readable_info)
        return True, info


class bus_station_callback(Callback.Callback):
    REQUEST_URL = "http://gzbusnow.sinaapp.com/index.php?"
    REQUEST_TIMEOUT = 5

    def _request_info(self, msg):
        url = bus_callback.REQUEST_URL + \
                urllib.urlencode({
                    'keyword': msg.encode('utf8'),
                    'a': 'query',
                    'c': 'station'
                    })
        try:
            rep = urllib2.urlopen(
                    url,
                    timeout=bus_callback.REQUEST_TIMEOUT) \
                .read()
            return rep
        except:
            return None

    def _parse_info(self, rep):
        res = []
        soup = BeautifulSoup(rep, from_encoding='utf-8')
        in_head = True
        for bus in soup.find_all('tr'):
            tds = bus.contents
            cur = {}
            if in_head:
                # cur['name'] = unicode(tds[0].string.strip())
                # cur['distance'] = unicode(tds[2].string.strip())
                # cur['info'] = unicode(tds[4].string.strip())
                in_head = False
                continue # escape header
            elif tds[3].string is not None:
                cur['name'] = unicode(tds[1].a.string.strip())
                cur['distance'] = unicode(tds[3].string.strip())
                cur['info'] = unicode(tds[5].string.strip())
            else:
                continue
            res.append(cur)
        return res

    def _bus_info(self, bus_number):
        info = self._request_info(bus_number)
        if info is None:
            return None
        else:
            parse_res = self._parse_info(info)
            if parse_res is None or len(parse_res) == 0:
                return None
            return parse_res

    def _readable_info(self, info):
        res = u""
        for bus in info:
            res += u"%s:\n  离本站%s站, 方向:%s\n\n" % (
                    bus['name'],
                    bus['distance'],
                    bus['info'])
        return res[:-2]

    def callback(self, cmd, action, target, msg, pre_value):
        if pre_value == "show" or pre_value == "get":
            if msg is None or len(msg) == 0:
                self._home.publish_msg(cmd, u"请输入公交站牌名称")
                return True, None
            self._home.publish_msg(cmd, u"正在查询...")
            info = self._bus_info(msg)
            if info is None:
                self._home.publish_msg(cmd, u"请输入正确的公交站牌名称")
                return True, None
            else:
                readable_info = self._readable_info(info)
                self._home.publish_msg(cmd, readable_info)
        return True, info


class time_callback(Callback.Callback):
    def callback(self, cmd, action, target, msg, pre_value):
        if pre_value == "show" or pre_value == "get":
            cur_datetime = datetime.now()
            if pre_value == "show":
                date_str = cur_datetime.strftime("%Y-%m-%d %H:%M:%S")
                self._home.publish_msg(cmd, date_str)
                DEBUG("time_callback: %s" % date_str)
            return True, cur_datetime
        else:
            return False


class volume_callback(Callback.Callback):
    def callback(self, cmd, action, target, msg, pre_value):
        if pre_value == "show" or pre_value == "get":
            volume = Sound.get_volume()
            if Util.empty_str(volume):
                self._home.publish_msg(cmd, u"获取音量值失败")
                return False
            if pre_value == "show":
                self._home.publish_msg(cmd, u"当前音量值为：%s" % volume)
            return True, int(volume)
        elif pre_value == "add" or pre_value == "new":
            volume = Sound.get_volume()
            if Util.empty_str(volume):
                self._home.publish_msg(cmd, u"获取音量值失败")
                return False
            if msg is None or len(msg) == 0:
                msg = "15"
            volume = int(volume) + int(msg)
            ret = Sound.set_volume(volume)
            if ret is None:
                self._home.publish_msg(cmd, u"设置音量值失败")
                return False
            if ret == "-2":
                self._home.publish_msg(cmd, u"音量值必须为整数")
                return False
            elif ret == "-3":
                self._home.publish_msg(cmd, u"音量值无效：%s" % volume)
                return False
            self._home.publish_msg(cmd, u"设置音量值为：%s" % volume)
            return True, volume
        elif pre_value == "lower":
            volume = Sound.get_volume()
            if Util.empty_str(volume):
                self._home.publish_msg(cmd, u"获取音量值失败")
                return False
            if msg is None or len(msg) == 0:
                msg = "15"
            volume = int(volume) - int(msg)
            ret = Sound.set_volume(volume)
            if ret is None:
                self._home.publish_msg(cmd, u"设置音量值失败")
                return False
            if ret == "-2":
                self._home.publish_msg(cmd, u"音量值必须为整数")
                return False
            elif ret == "-3":
                self._home.publish_msg(cmd, u"音量值无效：%s" % volume)
                return False
            self._home.publish_msg(cmd, u"设置音量值为：%s" % volume)
            return True, volume
        elif pre_value == "set" or pre_value == "resume":
            if pre_value == "resume":
                msg = self._home._storage.get("lehome:last_volume")
            if msg is None or len(msg) == 0:
                self._home.publish_msg(cmd, u"请输入音量值")
                return False

            # remember last volume value for resume volume
            volume = Sound.get_volume()
            if not Util.empty_str(volume):
                INFO("save last volume:%s" % volume)
                self._home._storage.set("lehome:last_volume", volume)

            ret = Sound.set_volume(msg)
            if ret is None:
                self._home.publish_msg(cmd, u"设置音量值失败")
                return False
            if ret == "-2":
                self._home.publish_msg(cmd, u"音量值必须为整数")
                return False
            elif ret == "-3":
                self._home.publish_msg(cmd, u"音量值无效：%s" % msg)
                return False
            self._home.publish_msg(cmd, u"设置音量值为：%s" % msg)
            return True, int(msg)
        else:
            return False


class fund_callback(Callback.Callback):

    FUND_SERVER_URL = "http://lehome.sinaapp.com/tool/fund?"
    FUND_REQUEST_TIMEOUT = 15

    def _req_fund_info(self, fund_id):
        url = fund_callback.FUND_SERVER_URL + \
                urllib.urlencode({
                    'id': fund_id,
                    })
        try:
            INFO("start fetching fund info:%s" % url)
            rep_text = urllib2.urlopen(
                    url,
                    timeout=fund_callback.FUND_REQUEST_TIMEOUT) \
                .read()
            INFO("got fund info:%s" % rep_text)

            rep = json.loads(rep_text)
            return rep
        except Exception, e:
            ERROR(e)
            return None

    def _format_fund_info(self, fund_id, fund_obj):
        ret = u"名称：" + fund_obj["name"] + "\n"
        ret += u"编号：" + fund_id + "\n"
        ret += u"当前价格：" + fund_obj["price"] + "\n"
        ret += u"当前涨幅：" + fund_obj["status"]
        return ret

    def callback(self, cmd, action, target, msg, pre_value):
        if pre_value == "show":
            fund_info = self._req_fund_info(msg.encode("utf-8"))
            INFO("got fund info:%s" % fund_info)
            if fund_info is None:
                self._home.publish_msg(cmd, u"无此基金:%s" % msg)
            else:
                self._home.publish_msg(
                            cmd,
                            self._format_fund_info(msg, fund_info)
                        )
        return True


class temperature_sensor_callback(Callback.Callback):
    def callback(self, cmd, action, target, msg, pre_value):
        addr = self._home._sensor.addr_for_place(msg)
        if addr is None:
            if pre_value == "show":
                self._home.publish_msg(cmd, u"无此处所%s" % msg)
            WARN("no such place:%s" % msg)
            return False
        if pre_value == "show" or pre_value == "get":
            state = self._home._sensor.get_temp(addr)
            try:
                state = int(state)
            except Exception, e:
                ERROR(e)
                ERROR("invaild temp value")
                self._home.publish_msg(cmd, u"无效的温度值")
                return False
            info = u'当前%s的温度为:%d℃' % (msg, state)
            if state is None:
                if pre_value == "show":
                    info = u'无法获取%s当前温度' % msg
                    INFO(info)
                    self._home.publish_msg(cmd, info)
                return False
            if pre_value == "show":
                INFO(info)
                self._home.publish_msg(cmd, info)
            return True, state
        else:
            return False


class humidity_sensor_callback(Callback.Callback):
    def callback(self, cmd, action, target, msg, pre_value):
        addr = self._home._sensor.addr_for_place(msg)
        if addr is None:
            if pre_value == "show":
                self._home.publish_msg(cmd, u"无此处所%s" % msg)
            WARN("no such place:%s" % msg)
            return False
        if pre_value == "show" or pre_value == "get":
            state = self._home._sensor.get_humidity(addr)
            try:
                state = int(state)
            except Exception, e:
                ERROR(e)
                ERROR("invaild hum value")
                self._home.publish_msg(cmd, u"无效的湿度值")
                return False
            info = u'当前%s的湿度为:%d%%' % (msg, state)
            if state is None:
                if pre_value == "show":
                    info = u'无法获取%s当前湿度' % msg
                    INFO(info)
                    self._home.publish_msg(cmd, info)
                return False
            if pre_value == "show":
                INFO(info)
                self._home.publish_msg(cmd, info)
            return True, state
        else:
            return False


class github_trending_callback(Callback.Callback):

    SERVICE_URL = "http://lehome.sinaapp.com/tool/github/trending"

    def _format_github_data(self, items):
        if items is None:
            return None
        ret = u""
        for item in items:
            ret += u"[ %s ]\n" % item["title"]
            ret += u"%s\n" % item["desc"]
            ret += u"%s\n" % item["href"]
            ret += u"\n"
        INFO(ret)
        return ret.strip()

    def _get_github_trending(self, lang, since):
        url = github_trending_callback.SERVICE_URL + "?" + \
                urllib.urlencode({'l':lang.encode('utf8'), 'since': since})
        INFO("sending:" + url)
        try:
            rep = urllib2.urlopen(url, timeout=10).read()
            rep_data = json.loads(rep)
            if rep_data["code"] != 200:
                return None
            return self._format_github_data(rep_data["data"])
        except Exception, e:
            EXCEPTION(e)
            return None

    def callback(self, cmd, action, target, msg, pre_value):
        if pre_value == "show" or pre_value == "push":
            since = "daily"
            if Util.empty_str(msg):
                msg = "java"
            params = msg.split("|")
            if len(params) == 2:
                msg = params[0]
                since = params[1]
            self._home.publish_msg(cmd, u"正在抓取数据...")
            content = self._get_github_trending(msg, since)
            if Util.empty_str(content):
                info = u'无法获取%s的Github trending' % msg
                INFO(info)
                self._home.publish_msg(cmd, info)
                return True
            INFO(content)
            self._home.publish_msg(cmd, content)
        return True
