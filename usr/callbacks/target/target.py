#!/usr/bin/env python
# encoding: utf-8

import glob
import types
import httplib
import json
import os
import errno
from datetime import datetime
from lib.sound import LE_Sound
from util.LE_Res import LE_Res
from lib.speech.LE_Speech import LE_Speech2Text
from lib.sound import LE_Sound

class target_callback:
    def callback(self,
            action=None,
            target=None,
            msg=None, 
            pre_value=None):
        print "* target callback: %s, message: %s pre_value: %s" %(target, msg, pre_value)
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

                LE_Speech2Text.pause()
                filepath = path + datetime.now().strftime("%m-%d_%H:%M") + ".mp3"
                record = pre_value
                record(filepath)
                LE_Sound.playmp3(
                                LE_Res.get_res_path("sound/com_stop")
                                )
                LE_Speech2Text.resume()
        elif action == u"播放":
            LE_Speech2Text.pause()

            if isinstance(pre_value, types.FunctionType):
                play = pre_value
                for idx, filepath in enumerate(glob.glob("usr/message/*.mp3")):
                    self._speaker.speak(u'第%d条留言' % (idx + 1))
                    play(filepath)

            LE_Sound.playmp3(
                            LE_Res.get_res_path("sound/com_stop")
                            )

            LE_Speech2Text.resume()
        return True, "pass"

