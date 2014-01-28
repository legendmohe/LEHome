#!/usr/bin/env python
# encoding: utf-8
import urllib2
import json

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

        return True, "weather"

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
        return True, "kill"

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
                    player = subprocess.Popen(['mpg123', path])
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
            return True, "pass"
