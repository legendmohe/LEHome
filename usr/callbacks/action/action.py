#!/usr/bin/env python
# encoding: utf-8
import subprocess
import os
from datetime import datetime
import threading
from lib.command.Command import Confirmation
from lib.sound import Sound
from util.Res import Res
from util.Util import parse_time, cn2dig
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


class switch_on_callback(Callback.Callback):
    def callback(self, cmd, action, target, msg):
        if target is None or len(target) == 0:
            WARN("no switch on target.")
            return True, False
        ip = self._home._switch.ip_for_name(target)
        if ip is None:
            WARN("invaild switch on target:" + target)
            self._home.publish_info(cmd, target + u"不存在")
            return True, False
        state = self._home._switch.show_state(ip)
        if state is None:
            self._home.publish_info(cmd, u"内部错误")
            return True, False
        elif state == "close":
            res = self._home._switch.send_open(ip)
            if res is None:
                self._home.publish_info(cmd, u"打开" + target + u"失败")
                return True, False
            elif res == "open":
                self._home.publish_info(cmd, u"已打开" + target)
                return True, "on"
            else:
                self._home.publish_info(cmd, u"打开" + target + u"失败")
                return True, False
        elif state == "open":
            self._home.publish_info(cmd, u"已打开" + target)
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
            self._home.publish_info(cmd, target + u"不存在")
            return True, False
        state = self._home._switch.show_state(ip)
        if state is None:
            self._home.publish_info(cmd, u"内部错误")
            return True, False
        elif state == "open":
            res = self._home._switch.send_close(ip)
            if res is None:
                self._home.publish_info(cmd, u"关闭" + target + u"失败")
                return True, False
            elif res == "close":
                self._home.publish_info(cmd, u"已关闭" + target)
                return True, "off"
            else:
                self._home.publish_info(cmd, u"关闭" + target + u"失败")
                return True, False
        elif state == "close":
            self._home.publish_info(cmd, u"已关闭" + target)
            return True, "off"
        return True, False


class stop_play_callback(Callback.Callback):
    def callback(self, action = None, target = None,
            msg = None, 
            pre_value = None):
        INFO("action:stop_play_callback invoke")
        if "player" in self._context:
            INFO("clear audio queue.")
            Sound.clear_queue()
            del self._context["player"]
            if "playlist" in self._context:
                del self._context["playlist"]
        return True, "stop_playing"


class play_callback(Callback.Callback):
    def callback(self, action = None, target = None,
            msg = None, pre_value = None):
        if target != None:
            def play(path = None, inqueue=True, loop=-1):
                if not path:
                    return
                if not "playlist" in self._context:
                    self._context["playlist"] = []
                playlist = self._context["playlist"]
                if not path in playlist:
                    playlist.append(path)
                    Sound.play(path, inqueue, loop)
                else:
                    INFO("%s was already in audio queue." % (path, ))
            if not "player" in self._context:
                self._context["player"] = play
            return True, "play"
        else:
            return True, "play"


class remove_callback(Callback.Callback):
    def callback(self,
            cmd=None,
            pre_value=None):
        
        self._speaker.speak(u'确认' + cmd + u'?')
        self._home.publish_info(cmd, u'确认' + cmd + u'?', cmd_type='confirm')
        cfm = Confirmation(self._home)
        is_cfm = cfm.confirm(ok=u'确认', cancel=u'取消')
        if is_cfm:
            return True, "remove"
        else:
            INFO("cancel")
            return False


class cal_callback(Callback.Callback):
    def callback(self,
            action=None,
            target=None,
            msg=None, 
            pre_value=None):
        return True, pre_value


threadlocal = threading.local()
class every_callback(Callback.Callback):
    def callback(self,
            action=None,
            target=None,
            msg=None,  # 每天 每*小时 每*分钟 每天*点*分
            pre_value=None):
        if pre_value != "while" or msg is None:       
            WARN("every callback must in a 'while'")
            return False, pre_value

        first_every_invoke = getattr(threadlocal, 'first_every_invoke', None)
        if first_every_invoke is None:
            threadlocal.first_every_invoke = True

        INFO("every_callback invoke:%s" % (msg, ))

        if msg.endswith(u"天"):
            if msg.startswith(u"天"):
                t = 24*60*60
            else:
                t = int(cn2dig(msg[:-1]))*24*60*60
        elif msg.endswith(u"小时"):
            if msg.startswith(u"小时"):
                t = 60*60
            else:
                t = int(cn2dig(msg[:-2]))*60*60
        elif msg.endswith(u"分钟"):
            if msg.startswith(u"分钟"):
                t = 60
            else:
                t = int(cn2dig(msg[:-2]))*60
        elif msg.startswith(u'天') \
                            and (msg.endswith(u'点') or msg.endswith(u'分')):
            t_list = parse_time(msg[1:]).split(":")
            target_hour = int(t_list[0])
            target_min = int(t_list[1])
            now = datetime.now()
            cur_hour = now.hour
            cur_min = now.minute
            if cur_hour <= target_hour and cur_min <= target_min:
                t = (target_hour - cur_hour)*60*60 + (target_min - cur_min)*60
                INFO("thread wait for %d sec" % (t, ))
                threading.current_thread().waitUtil(t)
            else:
                t = 24*60*60 - ((cur_hour - target_hour)*60*60 + (cur_min - target_min)*60)
                INFO("thread wait for %d sec" % (t, ))
                threading.current_thread().waitUtil(t)
            t = 24*60*60

        if threadlocal.first_every_invoke is False:
            INFO("thread wait for %d sec" % (t, ))
            threading.current_thread().waitUtil(t)
            if threading.current_thread().stopped():
                return False, False
            return True, True
        else:
            threadlocal.first_every_invoke = False
            if threading.current_thread().stopped():
                return False, False
            return True, True


class invoke_callback(Callback.Callback):
    def callback(self,
            action=None,
            target=None,
            msg=None,  # 执行*次
            pre_value=None):
        if pre_value == "while" and not msg is None:       
            if not msg.endswith(u'次'):
                INFO(u"loop not ends with 次")
                threading.current_thread().waitUtil(0.5) # time gap
                return True, True

            invoke_time = getattr(threadlocal, 'invoke_time', None)
            if invoke_time is None:
                threadlocal.invoke_time = 0

            times = int(cn2dig(msg[:-1]))
            INFO('invoke %s for %d times, current is %d'
                    % (action, times, threadlocal.invoke_time))
            if threadlocal.invoke_time < times:
                threadlocal.invoke_time += 1
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


class set_callback(Callback.Callback):
    def callback(self,
            action=None,
            target=None,
            msg=None, 
            pre_value=None):
        return True, "set"


class new_callback(Callback.Callback):
    def callback(self, cmd, target, pre_value):
        if not "recorder" in self._context:
            def record(path=None):
                if not path:
                    return
                INFO("record : " + path)

                if "record_process" in self._context:
                    record_process = self._context["record_process"]
                    if not record_process.poll():
                        record_process.kill()

                try:
                    record_process = subprocess.Popen([
                            "sudo",
                            "rec", path,
                            "rate", "16k",
                            "silence", "1", "0.1", "3%", "1", "3.0", "3%"])
                    self._context["record_process"] = record_process
                    record_process.wait()
                    if not record_process.poll():
                        record_process.kill()
                except Exception, ex:
                    ERROR(ex)
                del self._context["record_process"]

            self._context["recorder"] = record
        return True, "new"


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
        num = cn2dig(msg)
        if num is None:
            ERROR("num_value_callback num is invaild:" + msg)
            return False
        else:
            return True, num


class str_value_callback(Callback.Callback):
    def callback(self, msg):
        if msg is None:
            ERROR("str_value_callback msg is None.")
            return False
        else:
            return True, msg
