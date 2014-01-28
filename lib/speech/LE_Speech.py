#!/usr/bin/env python
# encoding: utf-8

from Queue import Queue, Empty
from collections import deque
from time import sleep
import subprocess
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
import logging as log


class LE_Speech2Text(object):
    PAUSE = False

    @classmethod
    def pause(cls):
        cls.PAUSE = True
        print "stt pause."

    @classmethod
    def resume(cls):
        cls.PAUSE = False
        print "stt resume."

    # @classmethod
    # def collect_noise(cls):
    #     print "preparing noise reduction."
    #     rec = subprocess.Popen(['rec', '-r', '16000', '-b', '16', 'noise.wav'])
    #     sleep(5)
    #     rec.kill()

    #     subprocess.call(
    #             ['sox', 'noise.wav', '-n', 'noiseprof', 'noise.prof']
    #             )
    #     print "finish preparing."

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
            print "Waiting write_queue to write all data"
            self.keep_streaming = False
            self.write_queue.join()
            print "Queue stop"

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
            req = urllib2.Request(xurl, data, headers)
            response = urllib2.urlopen(req)

            result = response.read().decode('utf-8')

            print "stt result: " + result

            list_data = json.loads(result)["hypotheses"]

            if len(list_data) != 0:
                return (list_data[0]["utterance"], list_data[0]["confidence"])

        def process_thread(self):
            while self.keep_streaming:
                try:
                    data = self.gen_data()
                    if self.keep_streaming and data:
                        result, conf = self.send_and_parse(data)
                        if result is not None:
                            self.callback(result, conf)
                        self.write_queue.task_done()
                except Empty:
                    pass
                except Exception, e:
                    print e

            print "end"

    class _filter:
        def _spectinvert(self, taps):
            l = len(taps)
            return ([0]*(l/2) + [1] + [0]*(l/2)) - taps

        def __init__(self, low, high, chunk, rate):
            print "init filter:\
                    low:%s high:%s chunk:%s rate:%s" \
                    % (low, high, chunk, rate)
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

        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 44100
        self.STT_RATE = 16000
        self.CHUNK_SIZE = 512  # !!!!!
        self.THRESHOLD = 1100.0
        self.BEGIN_THRESHOLD = 10
        self.TIMEOUT_THRESHOLD = self.BEGIN_THRESHOLD*3
        self.SILENTADDED = 0.5
        self._callback = callback

        self._processing_queue = Queue()

    def _normalize(self, snd_data):
        "Average the volume out"
        MAXIMUM = 16384
        times = float(MAXIMUM)/max(abs(i) for i in snd_data)
        r = array('h')
        for i in snd_data:
            r.append(int(i*times))
        return r

    def _add_silents(self, snd_data):
        r = array('h', [0 for i in xrange(int(self.SILENTADDED*self.RATE))])
        r.extend(snd_data)
        r.extend([0 for i in xrange(int(self.SILENTADDED*self.RATE))])
        return r

    def _is_silent(self, snd_data, sample_data):
        snd_data = np.fromstring(snd_data, dtype=np.int16)
        sample_data = list(sample_data)[0:self.BEGIN_THRESHOLD]
        sample_data = [max(x) for x in sample_data]
        snd_max = max(snd_data)
        # print snd_max
        return snd_max < self.THRESHOLD or \
                snd_max < 2.0*sum(sample_data)/len(sample_data)

        # as_ints = array('h', snd_data)
        # max_value = max(as_ints)
        # print max_value
        # return max_value < self.THRESHOLD

    def _wav_to_flac(self, wav_data):

        # wav_data = self._normalize(array('h', wav_data))
        # wav_data = self._add_silents(array('h', wav_data))
        # wav_data = pack('<' + ('h'*len(wav_data)), *wav_data)

        filename = 'output'
        wav_data = ''.join(wav_data)
        wf = wave.open(filename + '.wav', 'wb')
        wf.setnchannels(self.CHANNELS)
        wf.setsampwidth(self.SAMPLE_WIDTH)
        wf.setframerate(self.RATE)
        wf.writeframes(wav_data)
        wf.close()

        subprocess.call(
                ['sox', '--norm=-1', filename + '.wav',
                    '-r', str(self.STT_RATE), filename + '.flac']
                )
        # subprocess.call(
        #         ['sox', filename + '.flac', filename + '2.flac',
        #             'noisered', 'noise.prof']
        #         )
        with open(filename + '.flac', 'rb') as ff:
            flac_data = ff.read()

        # map(os.remove, (filename + '.flac', filename + '.wav'))
        return flac_data

    def _processing(self):
        sample_data = deque(maxlen=2*self.BEGIN_THRESHOLD)
        sample_data_should_load = True
        fil = self._filter(100.0, 3600.0, self.CHUNK_SIZE, self.RATE)

        while self.keep_running:
            record_begin = False
            snd_slient_finished = False
            snd_sound_finished = False
            num_silent = 0
            num_sound = 0
            sound_data = ""
            wnd_data = deque(maxlen=2*self.BEGIN_THRESHOLD)
            fil.reset()

            print "detecting:"
            while self.keep_running:
                try:
                    snd_data = self._processing_queue.get(block=True, timeout=2)
                except:
                    pass
                if snd_data is None:
                    continue
                snd_data = fil.filter(snd_data)

                if record_begin:
                    silent = self._is_silent(snd_data, sample_data)
                    sound_data += snd_data
                else:
                    wnd_data.append(snd_data)
                    if sample_data_should_load:
                        sample_data.append(
                                    np.fromstring(snd_data, dtype=np.int16)
                                )
                    silent = self._is_silent(snd_data, sample_data)

                # print silent
                if silent:
                    num_silent += 1
                    if num_sound < self.BEGIN_THRESHOLD:
                        num_sound = 0
                        snd_sound_finished = False
                    if num_silent > self.TIMEOUT_THRESHOLD:
                        snd_slient_finished = True
                    # enough time-gap for threshold
                    if num_silent > 2*self.TIMEOUT_THRESHOLD:
                        sample_data_should_load = True
                    else:
                        sample_data_should_load = False
                elif not silent:
                    num_sound += 1
                    if num_sound >= self.BEGIN_THRESHOLD and num_silent == 0:
                        snd_sound_finished = True
                        if not record_begin:
                            record_begin = True
                            sound_data += "".join(wnd_data)
                    num_silent = 0
                    snd_slient_finished = False

                if snd_slient_finished and snd_sound_finished:
                    print "data len: " + str(len(sound_data))
                    break

            sound_data = self._wav_to_flac(sound_data)
            self._queue.write_data(sound_data)

    def _recording(self):

        self._queue = self._queue(self._callback, rate=self.STT_RATE)
        self._queue.start()

        p = pyaudio.PyAudio()
        stream = p.open(format=self.FORMAT,
                    channels=self.CHANNELS,
                    rate=self.RATE,
                    input=True,
                    frames_per_buffer=self.CHUNK_SIZE)
        self.SAMPLE_WIDTH = p.get_sample_size(self.FORMAT)

        print "* recording"

        while self.keep_running:
            snd_data = stream.read(self.CHUNK_SIZE)
            if LE_Speech2Text.PAUSE is False:
                self._processing_queue.put(snd_data)
        
        print "* done recording"

        stream.stop_stream()
        stream.close()
        p.terminate()


    def start_recognizing(self):
        self.keep_running = True

        self._recording_thread = threading.Thread(target=self._recording)
        self._recording_thread.daemon = True
        self._recording_thread.start()

        self._processing_thread = threading.Thread(target=self._processing)
        self._processing_thread.daemon = True
        self._processing_thread.start()

    def stop_recognizing(self):
        self.keep_running = False # first
        self._queue.stop()

class LE_Text2Speech:

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
                print ex

    def __speakSpeechFromText(self, phrase):
        LE_Speech2Text.pause()
        googleSpeechURL = self.__getGoogleSpeechURL(phrase)
        subprocess.call(["mpg123", "-q", googleSpeechURL])
        LE_Speech2Text.resume()

    def start(self):
        log.info("speaker start.")
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
        log.info("speaker stop.")


    def speak(self, phrase, inqueue=False):
        if not self.__keep_speaking:
            log.warning("__keep_speaking is False.")
            return
        if isinstance(phrase, (list, tuple)):
            for item in phrase:
                if isinstance(item, unicode):
                    if inqueue is True:
                        self.__speak_queue.put(item)
                    else:
                        self.__speakSpeechFromText(item)
                else:
                    print "phrase must be unicode"
        else:
            if isinstance(phrase, unicode):
                if inqueue is True:
                    self.__speak_queue.put(phrase)
                else:
                    self.__speakSpeechFromText(phrase)
            else:
                print "phrase must be unicode"

if __name__ == '__main__':
    def callback(result, confidence):
        print "result: " + result + " | " + str(confidence)
    tts = LE_Text2Speech()
    tts.start()
    tts.speak([u"你好", u"今天天气真好"])

    recongizer = LE_Speech2Text(callback)
    recongizer.start_recognizing()
    sleep(100)
    recongizer.stop_recognizing()
    tts.stop()
    print "stop."
    # while True:
    #     sleep(0.1)
