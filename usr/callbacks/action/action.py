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

import subprocess
import urllib2
import urllib
import threading
import json
from lib.command.Command import Confirmation
from lib.sound import Sound
from lib.command.Command import UserInput
from util import Util
from util.log import *
from lib.model import Callback


class action_callback(Callback.Callback):
    def callback(self,
            cmd=None,
            action=None,
            target=None,
            msg=None, 
            pre_value=None):
        INFO("* action callback: %s, target: %s, message: %s pre_value: %s" %(action, target, msg, pre_value))
        return True, "pass"


class logical_value_callback(Callback.Callback):
    def callback(self, msg):
        if msg == u"真":
            return True, True
        elif msg == u"假":
            return True, False
        else:
            ERROR("logical_value_callback msg is invaild:" + msg)
            return False


class num_value_callback(Callback.Callback):
    def callback(self, msg):
        num = Util.cn2dig(msg)
        if num is None:
            ERROR("num_value_callback num is invaild:" + msg)
            return False
        else:
            return True, float(num)


class str_value_callback(Callback.Callback):
    def callback(self, msg):
        if msg is None:
            ERROR("str_value_callback msg is None.")
            return False
        else:
            return True, msg


class switch_on_callback(Callback.Callback):
    def callback(self, cmd, action, target, msg):
        if target is None or len(target) == 0:
            WARN("no switch on target.")
            return True, False
        ip = self._home._switch.ip_for_name(target)
        if ip is None:
            WARN("invaild switch on target:" + target)
            WARN("try ril:" + target)
            # self._home.publish_msg(cmd, target + u"不存在")
            return True, "on"
        state = self._home._switch.show_state(ip)
        if state is None:
            self._home.publish_msg(cmd, u"内部错误")
            return True, False
        elif state == "off":
            res = self._home._switch.send_open(ip)
            if res is None:
                self._home.publish_msg(cmd, u"打开" + target + u"失败")
                return True, False
            elif res == "+OK":
                self._home.publish_msg(cmd, u"已打开" + target)
                return True, "on"
            else:
                self._home.publish_msg(cmd, u"打开" + target + u"失败")
                return True, False
        elif state == "on":
            self._home.publish_msg(cmd, target + u"已经打开")
            return True, "on"
        return True, False


class switch_off_callback(Callback.Callback):
    def callback(self, cmd, action, target, msg):
        if target is None or len(target) == 0:
            WARN("no switch off target.")
            return True, False
        ip = self._home._switch.ip_for_name(target)
        if ip is None:
            WARN("invaild switch off target:" + target)
            WARN("try ril:" + target)
            # self._home.publish_msg(cmd, target + u"不存在")
            return True, "off"
        state = self._home._switch.show_state(ip)
        if state is None:
            self._home.publish_msg(cmd, u"内部错误")
            return True, False
        elif state == "on":
            res = self._home._switch.send_close(ip)
            if res is None:
                self._home.publish_msg(cmd, u"关闭" + target + u"失败")
                return True, False
            elif res == "+OK":
                self._home.publish_msg(cmd, u"已关闭" + target)
                return True, "off"
            else:
                self._home.publish_msg(cmd, u"关闭" + target + u"失败")
                return True, False
        elif state == "off":
            self._home.publish_msg(cmd, target + u"已经关闭")
            return True, "off"
        return True, False


class stop_play_callback(Callback.Callback):
    def callback(self, action = None, target = None,
            msg = None, 
            pre_value = None):
        INFO("action:stop_play_callback invoke")
        if "player" in self._global_context:
            INFO("clear audio queue.")
            Sound.clear_queue()
            del self._global_context["player"]
        return True, "stop_playing"


class play_callback(Callback.Callback):
    def callback(self, action = None, target = None,
            msg = None, pre_value = None):
        if target != None:
            def play(path = None, inqueue=True, loop=-1):
                if not path:
                    return
                Sound.play(path, inqueue, loop)
                INFO("%s going to audio queue." % (path, ))
            if not "player" in self._global_context:
                self._global_context["player"] = play
            return True, "play"
        else:
            return True, "play"


class remove_callback(Callback.Callback):
    def callback(self,
            cmd=None,
            pre_value=None):
        
        self._speaker.speak(u'确认' + cmd + u'?')
        self._home.publish_msg(cmd, u'确认' + cmd + u'?', cmd_type='confirm')
        cfm = Confirmation(self._home)
        is_cfm = cfm.confirm(ok=u'确认', cancel=u'取消')
        if is_cfm:
            return True, "remove"
        else:
            self._home.publish_msg(cmd, u'取消删除')
            INFO("cancel")
            return False


class every_callback(Callback.Callback):
    def callback(self, cmd, action, target, msg, pre_value, stack):
        if pre_value != "while" or msg is None:
            WARN("every callback must in a 'while'")
            return False, pre_value

        var_name = "first_every_invoke" + str(stack.cur_layer())
        first_every_invoke = stack.get_value(var_name)
        if first_every_invoke is None:
            self._home.publish_msg(cmd, u"循环建立:" + cmd)
            stack.set_var(var_name, True)

        # INFO("every_callback invoke:%s" % (msg, ))
        if msg.endswith(u"天"):
            if msg.startswith(u"天"):
                t = 24*60*60
            else:
                t = int(Util.cn2dig(msg[:-1]))*24*60*60
        elif msg.endswith(u"小时"):
            if msg.startswith(u"小时"):
                t = 60*60
            else:
                t = int(Util.cn2dig(msg[:-2]))*60*60
        elif msg.endswith(u"分钟"):
            if msg.startswith(u"分钟"):
                t = 60
            else:
                t = int(Util.cn2dig(msg[:-2]))*60
        elif msg.endswith(u"秒"):
            if msg.startswith(u"秒"):
                t = 1
            else:
                t = int(Util.cn2dig(msg[:-1]))
        elif (msg.startswith(u'天') or msg.startswith(u'工作日')) and \
             (msg.endswith(u'点') or msg.endswith(u'分')):
            # import pdb; pdb.set_trace()
            is_weekday = False
            if msg.startswith(u'工作日'):
                is_weekday = True
                msg = msg[3:]
            else:
                msg = msg[1:]

            period = msg.split(u'到')
            if len(period) == 2:
                t = Util.wait_for_period(period)
                if t == 0:
                    return True, True
                else:
                    DEBUG("period wait for %d sec" % (t, ))
                    threading.current_thread().waitUtil(t)
                    weekday = Util.what_day_is_today()
                    if weekday > 4 and is_weekday is True:
                        t = (7-weekday)*24*60*60
                        threading.current_thread().waitUtil(t)
                    if threading.current_thread().stopped():
                        return False, False
                    return True, True
            else:
                t = Util.gap_for_timestring(msg)
            if t >= 1:
                INFO("gap wait for %d sec" % (t, ))
                threading.current_thread().waitUtil(t)
                weekday = Util.what_day_is_today()
                if weekday > 4 and is_weekday is True:
                    t = (7-weekday)*24*60*60
                    INFO("weekday task, wait for %d sec" % (t, ))
                    threading.current_thread().waitUtil(t)
                if threading.current_thread().stopped():
                    return False, False
            return True, True
        else:
            self._home.publish_msg(cmd, u"时间格式有误")
            return False, False

        if stack.get_value(var_name) is False:
            threading.current_thread().waitUtil(t)
            if threading.current_thread().stopped():
                return False, False
            return True, True
        else:
            INFO("new loop for %d sec" % (t, ))
            stack.set_var(var_name, False)
            if threading.current_thread().stopped():
                return False, False
            return True, True


class invoke_callback(Callback.Callback):
    def callback(self, action, target, msg, pre_value, stack):
        if pre_value == "while" and not msg is None:
            if not msg.endswith(u'次'):
                INFO(u"loop not ends with 次")
                threading.current_thread().waitUtil(1)  # time gap
                return True, True
            var_name = "invoke_time" + str(stack.cur_layer())
            invoke_time = stack.get_value(var_name)
            if invoke_time is None:
                stack.set_var(var_name, 0)
                invoke_time = 0

            times = int(Util.cn2dig(msg[:-1]))
            INFO('invoke %s for %d times, current is %d'
                    % (action, times, invoke_time))
            if stack.get_value(var_name) < times:
                threading.current_thread().waitUtil(1) # time gap
                stack.set_var(var_name, invoke_time + 1)
                return True, True
            else:
                return True, False
        else:
            return True, "run"


class break_callback(Callback.Callback):
    def callback(self):
        return True, "break"


class show_callback(Callback.Callback):
    def callback(self, action, msg, target):
        return True, "show"


class get_callback(Callback.Callback):
    def callback(self, action, msg, target):
        return True, "get"


class set_callback(Callback.Callback):
    def callback(self,
            action=None,
            target=None,
            msg=None, 
            pre_value=None):
        return True, "set"


class new_callback(Callback.Callback):
    def callback(self, cmd, target, pre_value):
        if not "recorder" in self._global_context:
            def record(path=None):
                if not path:
                    return
                INFO("record : " + path)

                if "record_process" in self._global_context:
                    record_process = self._global_context["record_process"]
                    if not record_process.poll():
                        record_process.kill()

                try:
                    record_process = subprocess.Popen([
                            "sudo",
                            "rec", path,
                            "rate", "16k",
                            "silence", "1", "0.1", "3%", "1", "3.0", "3%"])
                    self._global_context["record_process"] = record_process
                    record_process.wait()
                    if not record_process.poll():
                        record_process.kill()
                except Exception, ex:
                    ERROR(ex)
                del self._global_context["record_process"]

            self._global_context["recorder"] = record
        return True, "new"
