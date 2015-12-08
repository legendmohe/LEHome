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


from Queue import Queue, Empty
from collections import deque
from time import sleep
import subprocess
# import math
import audioop
# import numpy as np
# import scipy.signal as signal
# from array import array
# from struct import pack
import pyaudio
import wave
# import urllib2
import urllib
import httplib
import json
import threading
import logging

import requests

from util.log import *
from lib.sound import Sound


# urllib2.install_opener(
#     urllib2.build_opener(
#         urllib2.ProxyHandler({'http': 'http://112.65.171.122:8080'})
#     )
# )


def process_ADP(wav_data, channels, width, rate, stt_rate):

    filename = 'data/output'
    wav_data = ''.join(wav_data)
    wf = wave.open(filename + '.wav', 'wb')
    wf.setnchannels(channels)
    wf.setsampwidth(width)
    wf.setframerate(rate)
    wf.writeframes(wav_data)
    wf.close()

    # subprocess.call(
    #         ['sox', filename + '.wav', filename + '_nf.wav',
    #             'noisered', 'data/noise.prof', '0.10']
    #         )
    # subprocess.call(
    #         ['sox', '--norm', filename + '_nf.wav',
    #             '-r', str(stt_rate), '-b', '16', '-c', '1', filename + '.wav']
    #         )
    subprocess.call(
            ['sox', filename + '.wav',
                '-r', str(stt_rate), '-b', '16', '-c', '1', filename + '_o.wav']
            )
    with open(filename + '_o.wav', 'rb') as ff:
        flac_data = ff.read()

    # INFO("data len: " + str(len(flac_data)))
    # map(os.remove, (filename + '.flac', filename + '.wav'))
    return flac_data

class Speech2Text(object):

    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    STT_RATE = 8000
    CHUNK_SIZE = 256  # !!!!!
    SAMPLE_WIDTH = 0

    BEGIN_THRESHOLD = 5
    RMS_THRESHOLD = 600
    CROSS_THRESHOLD = 300

    TIMEOUT_THRESHOLD = BEGIN_THRESHOLD*15
    WIND_THRESHOLD = BEGIN_THRESHOLD*3

    _PAUSE = False

    @classmethod
    def PAUSE(cls):
        cls._PAUSE = True
        INFO("stt pause.")

    @classmethod
    def RESUME(cls):
        cls._PAUSE = False
        INFO("stt resume.")

    # @classmethod
    # def collect_noise(cls):
    #     INFO("preparing noise reduction.")
    #     rec = subprocess.Popen(['rec', '-r', '%d' % Speech2Text.RATE,
    #                             '-b', '16',
    #                             '-c', '1',
    #                             'data/noise.wav'])
    #     sleep(1)
    #     rec.kill()
    #
    #     subprocess.call(
    #             ['sox', 'data/noise.wav', '-n', 'noiseprof', 'data/noise.prof']
    #             )
    #     INFO("finish preparing.")

    class _queue(object):

        HOST = "vop.baidu.com"
        CUID = "346826"
        APIKEY = "VuEFXGzV5yDqeiuos9xDDhSrG42Vvf3i"
        SECRETKEY = "Ie7vUgXkYfGedMwHKGbdVflw3dSI0aPa"

        def __init__(self, callback, rate=8000):
            self.write_queue = Queue()
            self.keep_streaming = True
            self.callback = callback
            self.rate = rate
            self.token = ""
            self.init_token()

        def init_token(self):

            host = "https://openapi.baidu.com/oauth/2.0/token?grant_type=client_credentials&client_id=%s&client_secret=%s" \
                % (Speech2Text._queue.APIKEY, Speech2Text._queue.SECRETKEY)
            try:
                token_res = urllib.urlopen(host).read()
                token_json = json.loads(token_res)
                self.token = token_json["access_token"]
                INFO("api token: %s", self.token)
            except Exception, ex:
                ERROR(ex)
                self.token = ""

        def start(self):
            self.process_thread = threading.Thread(target=self.process_thread)
            self.process_thread.daemon = True
            self.process_thread.start()

        def stop(self):
            DEBUG("Waiting write_queue to write all data")
            self.keep_streaming = False
            self.write_queue.join()
            DEBUG("Queue stop")

        def write_data(self, data):
            INFO("current queue size: %d" % self.write_queue.qsize())
            self.write_queue.put(data)

        def gen_data(self):
            if self.keep_streaming:
                data = self.write_queue.get(
                                        block=True,
                                        timeout=2
                                        ) # block!
                return data

        def send_and_parse(self, audio_data):
            content_len = len(audio_data)
            post_headers = {}
            post_headers["Content-Type"] = "audio/wav; rate=%d" % Speech2Text.STT_RATE
            post_headers["Content-Length"] = content_len
            post_url = "/server_api?cuid=" \
                    + Speech2Text._queue.CUID \
                    + "&token=" + self.token

            conn = httplib.HTTPConnection(Speech2Text._queue.HOST, timeout=5)
            conn.request("POST", post_url.encode('utf-8'), audio_data, post_headers)
            INFO('send audio data: %d' % content_len)
            response = conn.getresponse()
            data = response.read()
            if response.status == 200:
                json_res = json.loads(data)
                if json_res['err_no'] == 0:
                    res = json.loads(data)['result'][0]
                    return res, 1.0
            conn.close()
            return None, None

        def process_thread(self):
            while self.keep_streaming:
                try:
                    # data = self.gen_data()
                    data = process_ADP(self.gen_data(),
                                        Speech2Text.CHANNELS,
                                        Speech2Text.SAMPLE_WIDTH,
                                        Speech2Text.RATE,
                                        Speech2Text.STT_RATE)
                    if self.keep_streaming and data:
                        # if fatch token faild, fetch again here
                        if self.token == "":
                            self.init_token()
                        result, conf = self.send_and_parse(data)
                        if result is not None:
                            self.callback(result, conf)
                        else:
                            WARN("Speech2Text result is None.")
                        self.write_queue.task_done()
                except Empty:
                    pass
                except Exception, e:
                    ERROR(e)

            DEBUG("end")

    # class _filter:
    #     def _spectinvert(self, taps):
    #         l = len(taps)
    #         return ([0]*(l/2) + [1] + [0]*(l/2)) - taps
    #
    #     def __init__(self, low, high, chunk, rate):
    #         INFO("init filter: \nlow:%s high:%s chunk:%s rate:%s" \
    #                 % (low, high, chunk, rate))
    #         taps = chunk + 1
    #         fil_lowpass = signal.firwin(taps, low/(rate/2))
    #         fil_highpass = self._spectinvert(
    #                             signal.firwin(taps, high/(rate/2))
    #                             )
    #         fil_bandreject = fil_lowpass+fil_highpass
    #         fil_bandpass = self._spectinvert(fil_bandreject)
    #
    #         self._fil = fil_bandpass
    #         self._zi = [0]*(taps-1)
    #         self._taps = taps
    #
    #     def reset(self):
    #         self._zi = [0]*(self._taps - 1)
    #
    #     def filter(self, data):
    #         data = np.fromstring(data, dtype=np.int16)
    #         (data, self._zi) = signal.lfilter(self._fil, 1, data, -1, self._zi)
    #         return data.astype(np.int16).tostring()

    def __init__(self, callback):
        self.keep_running = False
        self._pause = False

        self.callback = callback

        self._processing_queue = Queue()

    def _is_silent(self, wnd_data):
        wnd_data = ''.join(wnd_data)
        cross = audioop.cross(wnd_data, 2)
        rms = audioop.rms(wnd_data, 2)
        # print cross, rms
        # return True
        return (cross > Speech2Text.CROSS_THRESHOLD) or (rms < Speech2Text.RMS_THRESHOLD)


    def _processing(self):
        # fil = self._filter(100.0, 3000.0, Speech2Text.CHUNK_SIZE, Speech2Text.RATE)
        wnd_data = deque(maxlen=Speech2Text.WIND_THRESHOLD)

        while self.keep_running:
            record_begin = False
            snd_slient_finished = False
            snd_sound_finished = False
            num_silent = 0
            num_sound = 0
            sound_data = ""
            # fil.reset()

            INFO("detecting:")
            while self.keep_running:
                try:
                    snd_data = self._processing_queue.get(block=True, timeout=2)
                except:
                    continue

                # snd_data = fil.filter(snd_data)
                wnd_data.append(snd_data)
                silent = self._is_silent(wnd_data)
                # if silent:
                #     snd_data = '\x00' * Speech2Text.CHUNK_SIZE
                if record_begin:
                    sound_data += snd_data

                # if silent is False:
                #     print silent
                # print num_silent
                if silent:
                    num_silent += 1
                    if num_sound < Speech2Text.BEGIN_THRESHOLD:
                        num_sound = 0
                        snd_sound_finished = False
                    if num_silent > Speech2Text.TIMEOUT_THRESHOLD:
                        snd_slient_finished = True
                elif not silent:
                    num_sound += 1
                    if num_sound >= Speech2Text.BEGIN_THRESHOLD and num_silent == 0:
                        snd_sound_finished = True
                        if not record_begin:
                            record_begin = True
                            sound_data += "".join(wnd_data)
                    num_silent = 0
                    snd_slient_finished = False

                if snd_slient_finished and snd_sound_finished:
                    break

            self.queue.write_data(sound_data)

    def _recording(self):
        p = pyaudio.PyAudio()
        stream = p.open(format=Speech2Text.FORMAT,
                    channels=Speech2Text.CHANNELS,
                    rate=Speech2Text.RATE,
                    input=True,
                    frames_per_buffer=Speech2Text.CHUNK_SIZE)
        Speech2Text.SAMPLE_WIDTH = p.get_sample_size(Speech2Text.FORMAT)
        # Speech2Text.RATE = p.get_device_info_by_index(0)['defaultSampleRate']
        INFO("default rate: %d" % (Speech2Text.RATE,))

        self.queue = self._queue(self.callback, rate=Speech2Text.STT_RATE)
        self.queue.start()

        INFO("* recording")

        while self.keep_running:
            try:
                snd_data = stream.read(Speech2Text.CHUNK_SIZE)
            except IOError as ex:
                print "OverflowError" + str(ex)
                if ex[1] != pyaudio.paInputOverflowed:
                    raise
                snd_data = '\x00' * Speech2Text.CHUNK_SIZE
            if Speech2Text._PAUSE is False and self._pause is False:
                self._processing_queue.put(snd_data)
        
        INFO("* done recording")

        stream.stop_stream()
        stream.close()
        p.terminate()


    def start_recognizing(self):
        self.keep_running = True

        self._recording_thread = threading.Thread(target=self._recording)
        self._recording_thread.daemon = True
        self._recording_thread.start()

        sleep(1)

        self._processing_thread = threading.Thread(target=self._processing)
        self._processing_thread.daemon = True
        self._processing_thread.start()

    def stop_recognizing(self):
        self.keep_running = False # first
        self.queue.stop()

    def pause(self):
        self._pause = True
        INFO("stt pause.")

    def resume(self):
        self._pause = False
        INFO("stt resume.")

class Text2Speech:

    BASE_OAUTH_URL = "http://openapi.baidu.com/oauth/2.0/token"
    BASE_OAUTH_DATA = {
        "grant_type": "client_credentials",
        "client_id": "7P5ZCG6WTAGWr5TuURBgndRH",
        "client_secret": "gggk30ubCSFGM5uXYfwGll4vILlnQ0em",
    }
    BASE_TTS_URL = "http://tsn.baidu.com/text2audio"

    def __init__(self):
        self.__token = None

    def __doTTS(self, phrase, inqueue):
        if self.__token is None or len(self.__token) == 0:
            ERROR("invalid tts token.")
            return
            
        tts_data = {
            "tok": self.__token,
            "lan": "zh",
            "tex": phrase.encode("utf-8"),
            "ctp": 1,
            "spd": 7,
            "pit": 3,
            "per": 0,
            "cuid": "lehome"
        }
        data = urllib.urlencode(tts_data)
        tts_url = "%s?%s" % (Text2Speech.BASE_TTS_URL, data)
        Sound.play(tts_url, channel="notice", inqueue=inqueue)
        
    def __get_access_token(self):
#        proxies = {
#          "http": "109.131.7.11:8080",
#        }

        r = requests.post(
                        Text2Speech.BASE_OAUTH_URL,
                        data = Text2Speech.BASE_OAUTH_DATA,
#                        proxies=proxies
        )
        try:
            auth_rep = json.loads(r.content)
        except Exception, ex:
            ERROR(ex)
            ERROR("cannot get tts auth token.")
            return None

        access_token = auth_rep["access_token"]
        INFO("got token %s" % access_token)
        return access_token

    def start(self):
        self.__token = self.__get_access_token()
        INFO("speaker start.")

    def speak(self, phrase, inqueue=True):
        if isinstance(phrase, (list, tuple)):
            for item in phrase:
                if isinstance(item, unicode):
                    self.__doTTS(item, inqueue)
                else:
                    ERROR("phrase must be unicode")
        else:
            if isinstance(phrase, unicode):
                self.__doTTS(phrase, inqueue)
            else:
                ERROR("phrase must be unicode")

if __name__ == '__main__':
    def callback(result, confidence):
        print "result: " + result + " | " + str(confidence)
    # tts = Text2Speech()
    # tts.start()
    # tts.speak([u"你好", u"今天天气真好"])

    # Speech2Text.collect_noise()
    recongizer = Speech2Text(callback)
    recongizer.start_recognizing()
    sleep(100)
    recongizer.stop_recognizing()
    # tts.stop()
    print "stop."
    # while True:
    #     sleep(0.1)
