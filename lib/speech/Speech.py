#!/usr/bin/env python
# encoding: utf-8

from Queue import Queue, Empty
from collections import deque
from time import sleep
import subprocess
import math
import audioop
import numpy as np
import scipy.signal as signal
from array import array
from struct import pack
import pyaudio
import wave
import urllib2
import urllib
import json
import threading
from util.log import *
from lib.sound import Sound


# urllib2.install_opener(
#     urllib2.build_opener(
#         urllib2.ProxyHandler({'http': 'http://112.65.171.122:8080'})
#     )
# )


def wav_to_flac(wav_data, channels, width, rate, stt_rate):

    filename = 'output'
    wav_data = ''.join(wav_data)
    wf = wave.open(filename + '.wav', 'wb')
    wf.setnchannels(channels)
    wf.setsampwidth(width)
    wf.setframerate(rate)
    wf.writeframes(wav_data)
    wf.close()

    subprocess.call(
            ['sox', filename + '.wav', filename + '_nf.wav',
                'noisered', 'noise.prof', '0.10']
            )
    subprocess.call(
            ['sox', '--norm', filename + '_nf.wav',
                '-r', str(stt_rate), filename + '.flac']
            )
    with open(filename + '.flac', 'rb') as ff:
        flac_data = ff.read()

    INFO("data len: " + str(len(flac_data)))
    # map(os.remove, (filename + '.flac', filename + '.wav'))
    return flac_data

class Speech2Text(object):

    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    STT_RATE = 16000
    CHUNK_SIZE = 256  # !!!!!
    SAMPLE_WIDTH = 0

    BEGIN_THRESHOLD = 5
    RMS_THRESHOLD = 200
    CROSS_THRESHOLD = 500

    TIMEOUT_THRESHOLD = BEGIN_THRESHOLD*10
    WIND_THRESHOLD = BEGIN_THRESHOLD*2

    _PAUSE = False

    @classmethod
    def PAUSE(cls):
        cls._PAUSE = True
        INFO("stt pause.")

    @classmethod
    def RESUME(cls):
        cls._PAUSE = False
        INFO("stt resume.")

    @classmethod
    def collect_noise(cls):
        INFO("preparing noise reduction.")
        rec = subprocess.Popen(['rec', '-r', '16000',
                                '-b', '16',
                                '-c', '1',
                                'noise.wav'])
        sleep(1)
        rec.kill()

        subprocess.call(
                ['sox', 'noise.wav', '-n', 'noiseprof', 'noise.prof']
                )
        INFO("finish preparing.")

    class _queue(object):

        def __init__(self, callback, lang="zh-CN", rate=16000):
            self.write_queue = Queue()
            self.keep_streaming = True
            self.callback = callback
            self.lang = lang
            self.rate = rate

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
            self.write_queue.put(data)

        def gen_data(self):
            if self.keep_streaming:
                data = self.write_queue.get(
                                        block=True,
                                        timeout=2
                                        ) # block!
                return data

        def send_and_parse(self, data):
            xurl = 'http://www.google.com/speech-api/v1/recognize?xjerr=1&client=chromium&lang=' + self.lang
            content_type = 'audio/x-flac; rate=' + str(self.rate)
            headers = {'Content-Type':content_type}
            try:
                req = urllib2.Request(xurl, data, headers)
                response = urllib2.urlopen(req)

                result = response.read().decode('utf-8')
            except Exception, ex:
                ERROR("request error:", ex)
                return None, None

            DEBUG("stt result: " + result)

            list_data = json.loads(result)["hypotheses"]

            if len(list_data) != 0:
                return (list_data[0]["utterance"], list_data[0]["confidence"])
            return None, None

        def process_thread(self):
            while self.keep_streaming:
                try:
                    data = wav_to_flac(self.gen_data(),
                                        Speech2Text.CHANNELS,
                                        Speech2Text.SAMPLE_WIDTH,
                                        Speech2Text.RATE,
                                        Speech2Text.STT_RATE)
                    if self.keep_streaming and data:
                        result, conf = self.send_and_parse(data)
                        if result is not None:
                            self.callback(result, conf)
                        self.write_queue.task_done()
                except Empty:
                    pass
                except Exception, e:
                    ERROR(e)

            DEBUG("end")

    class _filter:
        def _spectinvert(self, taps):
            l = len(taps)
            return ([0]*(l/2) + [1] + [0]*(l/2)) - taps

        def __init__(self, low, high, chunk, rate):
            INFO("init filter:\
                    low:%s high:%s chunk:%s rate:%s" \
                    % (low, high, chunk, rate))
            taps = chunk + 1
            fil_lowpass = signal.firwin(taps, low/(rate/2))
            fil_highpass = self._spectinvert(
                                signal.firwin(taps, high/(rate/2))
                                )
            fil_bandreject = fil_lowpass+fil_highpass
            fil_bandpass = self._spectinvert(fil_bandreject)

            self._fil = fil_bandpass
            self._zi = [0]*(taps-1)
            self._taps = taps

        def reset(self):
            self._zi = [0]*(self._taps - 1)

        def filter(self, data):
            data = np.fromstring(data, dtype=np.int16)
            (data, self._zi) = signal.lfilter(self._fil, 1, data, -1, self._zi)
            return data.astype(np.int16).tostring()

    def __init__(self, callback):
        self.keep_running = False
        self._pause = False

        self.callback = callback

        self._processing_queue = Queue()

    def _is_silent(self, wnd_data):
        wnd_data = ''.join(wnd_data)
        cross = audioop.cross(wnd_data, 2)
        rms = audioop.rms(wnd_data, 2)
        print cross, rms
        # return True
        return (cross > Speech2Text.CROSS_THRESHOLD) or (rms < Speech2Text.RMS_THRESHOLD)


    def _processing(self):
        fil = self._filter(100.0, 3000.0, Speech2Text.CHUNK_SIZE, Speech2Text.RATE)
        wnd_data = deque(maxlen=Speech2Text.WIND_THRESHOLD)

        while self.keep_running:
            record_begin = False
            snd_slient_finished = False
            snd_sound_finished = False
            num_silent = 0
            num_sound = 0
            sound_data = ""
            fil.reset()

            INFO("detecting:")
            while self.keep_running:
                try:
                    snd_data = self._processing_queue.get(block=True, timeout=2)
                except:
                    continue

                snd_data = fil.filter(snd_data)
                wnd_data.append(snd_data)
                silent = self._is_silent(wnd_data)
                # if silent:
                #     snd_data = '\x00' * Speech2Text.CHUNK_SIZE
                if record_begin:
                    sound_data += snd_data

                # print silent
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
        INFO("default rate:", Speech2Text.RATE)

        self.queue = self._queue(self.callback, rate=Speech2Text.STT_RATE)
        self.queue.start()

        INFO("* recording")

        while self.keep_running:
            try:
                snd_data = stream.read(Speech2Text.CHUNK_SIZE)
            except IOError as ex:
                print "OverflowError"
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

    def __init__(self):
        self.__speak_queue = Queue()
        self.__keep_speaking = False

    def __getGoogleSpeechURL(self, phrase):
        googleTranslateURL = "http://translate.google.com/translate_tts"
        parameters = {
                "tl" : "zh-CN",
                "q": phrase.encode("utf-8"),
                "ie": "utf-8",
                "oe" : "utf-8"
                }
        data = urllib.urlencode(parameters)
        googleTranslateURL = "%s?%s" % (googleTranslateURL,data)
        return googleTranslateURL

    def __speak_worker(self):
        while self.__keep_speaking:
            try:
                phrase = self.__speak_queue.get(block=True, timeout=2)
                self.__speakSpeechFromText(phrase)
                self.__speak_queue.task_done()
            except Empty:
                pass
            except Exception, ex:
                ERROR(ex)

    def __speakSpeechFromText(self, phrase):
        googleSpeechURL = self.__getGoogleSpeechURL(phrase)
        INFO("text2speech retrive from: " + googleSpeechURL)
        Sound.play(googleSpeechURL, inqueue=True)
        # subprocess.call(["mpg123", "-q", googleSpeechURL])

    def start(self):
        INFO("speaker start.")
        self.__keep_speaking = True
        self.__speak_thread = threading.Thread(target=self.__speak_worker)
        self.__speak_thread.daemon = True
        self.__speak_thread.start()

    def stop(self):
        self.__keep_speaking = False
        with self.__speak_queue.mutex:
            self.__speak_queue.queue.clear()
        # self.__speak_queue.join()
        self.__speak_thread.join()
        INFO("speaker stop.")

    def speak(self, phrase, inqueue=False):
        print phrase
        if not self.__keep_speaking:
            WARN("__keep_speaking is False.")
            return
        if isinstance(phrase, (list, tuple)):
            for item in phrase:
                if isinstance(item, unicode):
                    if inqueue is True:
                        self.__speak_queue.put(item)
                    else:
                        self.__speakSpeechFromText(item)
                else:
                    ERROR("phrase must be unicode")
        else:
            if isinstance(phrase, unicode):
                if inqueue is True:
                    self.__speak_queue.put(phrase)
                else:
                    self.__speakSpeechFromText(phrase)
            else:
                ERROR("phrase must be unicode")

if __name__ == '__main__':
    def callback(result, confidence):
        print "result: " + result + " | " + str(confidence)
    tts = Text2Speech()
    tts.start()
    tts.speak([u"你好", u"今天天气真好"])

    recongizer = Speech2Text(callback)
    recongizer.start_recognizing()
    sleep(100)
    recongizer.stop_recognizing()
    tts.stop()
    print "stop."
    # while True:
    #     sleep(0.1)
