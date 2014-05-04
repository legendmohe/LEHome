#!/usr/bin/env python
# encoding: utf-8
import urllib2
import json
import subprocess
import glob
import os
import time
import datetime
import threading
from lib.command.Command import Comfirmation
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
        DEBUG("* action callback: %s, target: %s, message: %s pre_value: %s" %(action, target, msg, pre_value))
        return True, "pass"

class weather_report_callback(Callback.Callback):
    def callback(self,
            action=None,
            target=None,
            msg=None, 
            pre_value=None):
        
        url = 'http://m.weather.com.cn/data/101280101.html'  # GUangzhou

        re = urllib2.urlopen(url).read()
        re = re.decode('UTF-8')
        we = json.loads(re)['weatherinfo']

        INFO(u'城市：' + we['city'])
        INFO(u'日期：' + we['date_y'])
        INFO(u'week：' + we['week'])
        INFO(u'未来6天天气：')
        INFO('\t' + we['temp1'] + '\t' + we['weather1'] + '\t' + we['wind1'])
        INFO('\t' + we['temp2'] + '\t' + we['weather2'] + '\t' + we['wind2'])
        INFO('\t' + we['temp3'] + '\t' + we['weather3'] + '\t' + we['wind3'])
        INFO('\t' + we['temp4'] + '\t' + we['weather4'] + '\t' + we['wind4'])
        INFO('\t' + we['temp5'] + '\t' + we['weather5'] + '\t' + we['wind5'])
        INFO('\t' + we['temp6'] + '\t' + we['weather6'] + '\t' + we['wind6'])
        INFO(u'穿衣指数: '+ we['index_d'])
        INFO(u'紫外线: ' + we['index_uv'])
        
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

        return True, pre_value

class stop_play_callback(Callback.Callback):
    def callback(self, action = None, target = None,
            msg = None, 
            pre_value = None):
        INFO("action:stop_play_callback invoke")
        if "playlist" in self._context.keys():
            INFO("clear audio queue.")
            Sound.clear_queue()
        return True, pre_value


class play_callback(Callback.Callback):
    def callback(self, action = None, target = None,
            msg = None, pre_value = None):
        if action == u"播放" and target != None:
            def play(path = None):
                if not path:
                    return

                if not "playlist" in self._context:
                    self._context["playlist"] = []

                playlist = self._context["playlist"]
                if not path in playlist:
                    Sound.play(path, inqueue=True)
                else:
                    INFO("%s was already in audio queue." % (path, ))

            return True, play
        else:
            return True, pre_value


class remove_callback(Callback.Callback):
    def callback(self,
            cmd=None,
            pre_value=None):
        
        self._speaker.speak(u'确认' + cmd + u'?')
        self._home.publish_info(cmd, u'确认' + cmd + u'?')
        cfm = Comfirmation(self._home)
        is_cfm = cfm.confirm()
        if is_cfm:
            return True, pre_value
        else:
            INFO("cancel")
            return False, pre_value


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
            INFO("thread wait util %s" % (msg, ))
            t_list = parse_time(msg[1:]).split(":")
            target_hour = int(t_list[0])
            target_min = int(t_list[1])
            now = datetime.now()
            cur_hour = now.hour
            cur_min = now.minute
            if cur_hour <= target_hour:
                threading.current_thread().waitUtil(
                    (target_hour - cur_hour)*60*60 + (target_min - cur_min)*60
                    )
            else:
                threading.current_thread().waitUtil(
                24*60*60 -
                ((cur_hour - target_hour)*60*60 + (cur_min - target_min)*60)
                )
            t = 24*60*60

        if threadlocal.first_every_invoke is False:
            threading.current_thread().waitUtil(t)
            if threading.current_thread().stopped():
                return False, False
            return True, True
        else:
            threadlocal.first_every_invoke = False
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
            return True, True


class break_callback(Callback.Callback):
    def callback(self):
        return True, True


class show_callback(Callback.Callback):
    def callback(self, action, msg, target):
        return True, True


class memo_callback(Callback.Callback):
    def callback(self,
            action=None,
            target=None,
            msg=None, 
            pre_value=None):
        
        if action == u"录音" and target == None:
            try:
                path = "usr/memo/"
                try:
                    os.makedirs(path)
                except OSError as exc:
                    if exc.errno == errno.EEXIST and os.path.isdir(path):
                        pass
                    else:
                        ERROR(exc)
                        return True, "pass"

                self._home.setResume(True)
                filepath = path + datetime.now().strftime("%y-%m-%d_%H:%M:%S") + ".mp3"
                subprocess.call([
                        "rec", path,
                        "rate", "16k",
                        "silence", "1", "0.1", "3%", "1", "5.0", "3%"])
                Sound.play(
                            Res.get_res_path("sound/com_stop")
                            )
                self._home.setResume(False)
            except Exception, ex:
                ERROR(ex)
        return True, pre_value


class set_callback(Callback.Callback):
    def callback(self,
            action=None,
            target=None,
            msg=None, 
            pre_value=None):
        return True, pre_value


class add_callback(Callback.Callback):
    def callback(self, cmd, target, pre_value):
        if target == u"录音":
            def record(path=None):
                if not path:
                    return
                INFO("record : " + path)

                if "recorder" in self._context:
                    recorder = self._context["recorder"]
                    if not recorder.poll():
                        recorder.kill()

                import subprocess
                try:
                    recorder = subprocess.Popen([
                            "sudo",
                            "rec", path,
                            "rate", "16k",
                            "silence", "1", "0.1", "3%", "1", "3.0", "3%"])
                    self._context["recorder"] = recorder
                    recorder.wait()
                    if not recorder.poll():
                        recorder.kill()
                except Exception, ex:
                    ERROR(ex)
                del self._context["recorder"]
            
            return True, record
        else:
            return True, pre_value
