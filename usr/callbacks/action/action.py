#!/usr/bin/env python
# encoding: utf-8
import urllib2
import json
import subprocess
import glob, os
from lib.command.Command import Comfirmation
from lib.sound import Sound
from util.Res import Res
from util.Util import parse_time


class action_callback:
    def callback(self,
            action=None,
            target=None,
            msg=None, 
            pre_value=None):
        print "* action callback: %s, target: %s, message: %s pre_value: %s" %(action, target, msg, pre_value)
        return True, "pass"

class weather_report_callback:
    def callback(self,
            action=None,
            target=None,
            msg=None, 
            pre_value=None):
        
        url = 'http://m.weather.com.cn/data/101280101.html'

        re = urllib2.urlopen(url).read()
        re = re.decode('UTF-8')
        we = json.loads(re)['weatherinfo']

        print u'城市：' + we['city']
        print u'日期：' + we['date_y']
        print u'week：' + we['week']
        print u'未来6天天气：'
        print '\t' + we['temp1'] + '\t' + we['weather1'] + '\t' + we['wind1']
        print '\t' + we['temp2'] + '\t' + we['weather2'] + '\t' + we['wind2']
        print '\t' + we['temp3'] + '\t' + we['weather3'] + '\t' + we['wind3']
        print '\t' + we['temp4'] + '\t' + we['weather4'] + '\t' + we['wind4']
        print '\t' + we['temp5'] + '\t' + we['weather5'] + '\t' + we['wind5']
        print '\t' + we['temp6'] + '\t' + we['weather6'] + '\t' + we['wind6']
        print u'穿衣指数: '+ we['index_d'] 
        print u'紫外线: ' + we['index_uv']
        
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

class stop_play_callback:
    def callback(self, action = None, target = None,
            msg = None, 
            pre_value = None):
        if "player" in self._context.keys():
            try:
                print "stop playing misic."
                player = self._context["player"]
                print "killing: " + str(player)
                if not player.poll():
                    player.kill()
            except Exception,ex:
                print ex
        return True, pre_value

class play_callback:
    def callback(self, action = None, target = None,
            msg = None, pre_value = None):
        if action == u"播放" and target != None:
            def play(path = None):
                if not path:
                    return
                print "play music: " + path

                if "player" in self._context:
                    player = self._context["player"]
                    if not player.poll():
                        player.kill()

                import subprocess
                try:
                    player = subprocess.Popen(['sudo', 'play', path])
                    self._context["player"] = player
                    player.wait()
                    if not player.poll():
                        player.kill()
                except Exception, ex:
                    print "music stop."
                    # print ex
                del self._context["player"]
            
            return True, play
        else:
            return True, pre_value

class remove_callback:
    def callback(self,
            action=None,
            target=None,
            msg=None, 
            pre_value=None):
        
        self._speaker.speak(u'确认删除' + msg + u'?')
        cfm = Comfirmation(self._home)
        is_cfm = cfm.confirm()
        if is_cfm:
            if target == u"留言":
                filelist = glob.glob("usr/message/*.mp3")
                for f in filelist:
                    os.remove(f)
                    print "remove:%s" % (f)
            Sound.playmp3(
                            Res.get_res_path("sound/com_trash")
                            )
        else:
            print u"cancel"

        return True, pre_value

class record_callback:
    def callback(self,
            action=None,
            target=None,
            msg=None, 
            pre_value=None):

        if action == u"记录" and target != None:
            def record(path=None):
                if not path:
                    return
                print "record : " + path

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
                    print " stop."
                    # print ex
                del self._context["recorder"]
            
            return True, record
        else:
            return True, pre_value

class cal_callback:
    def callback(self,
            action=None,
            target=None,
            msg=None, 
            pre_value=None):
        

        return True, pre_value

class every_callback:
    def callback(self,
            action=None,
            target=None,
            msg=None,  # 每*小时 每*分钟 每天*点*分
            pre_value=None):
        if pre_value != "while" or msg is None:       
            return False, None

        if msg.startswith(u"天"):
            t = Util.parse_time(msg[1:])
        elif msg.endswith(u"分") or msg.endswith(u"分钟"):
            t = Util.parse_time(msg)
        
        return True, pre_value

class memo_callback:
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
                        print exc
                        return True, "pass"

                self._home.setResume(True)
                filepath = path + datetime.now().strftime("%y-%m-%d_%H:%M:%S") + ".mp3"
                subprocess.call([
                        "rec", path,
                        "rate", "16k",
                        "silence", "1", "0.1", "3%", "1", "5.0", "3%"])
                Sound.playmp3(
                                Res.get_res_path("sound/com_stop")
                                )
                self._home.setResume(False)
            except Exception, ex:
                print " stop."
                # print ex
        return True, pre_value

class set_callback:
    def callback(self,
            action=None,
            target=None,
            msg=None, 
            pre_value=None):
        return True, pre_value
