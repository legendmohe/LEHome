#!/usr/bin/env python
# encoding: utf-8

from sys import byteorder
from array import array
from struct import pack, unpack
from Queue import Queue
from collections import deque
from time import sleep
import flac.encoder as encoder
import sys, os, subprocess
import math
import numpy as np
import pyaudio, wave
import urllib2, urllib
import json 
import threading
import logging as log

class LE_Speech2Text(object):

    class _queue(object):

        def __init__(self, callback, lang = "zh-CN"):
            self.write_queue = Queue()
            self.keep_streaming = True
            self.RATE = 16000
            self.callback = callback
            self.lang = lang

        def start(self):
            self.process_thread = threading.Thread(target=self.process_thread)
            self.process_thread.daemon = True
            self.process_thread.start()

        def stop(self):
            print "Waiting write_queue to write all data"
            self.keep_streaming=False
            self.write_queue.join()
            print "Queue stop"

        def write_data(self, data):
            self.write_queue.put(data)

        def gen_data(self):
            if self.keep_streaming:
                data = self.write_queue.get(block=True, timeout=2) # block!
                return data

        def send_and_parse(self, data):
            xurl = 'http://www.google.com/speech-api/v1/recognize?xjerr=1&client=chromium&lang=' + self.lang
            headers = {'Content-Type' : 'audio/x-flac; rate=16000'}
            req = urllib2.Request(xurl, data, headers)
            response = urllib2.urlopen(req)

            strlist = response.read().decode('utf-8')

            print "strlist" + strlist

            list_data = json.loads(strlist)["hypotheses"]

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
                except Exception, e:
                    # print e
                    pass

            print "end"

    def __init__(self, callback):
        self.keep_running = False
        self._condition = threading.Condition()

        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000
        self.CHUNK_SIZE = 256 #!!!!!
        self.THRESHOLD = 1300
        self.BEGIN_THRESHOLD = 4
        self.TIMEOUT_THRESHOLD = 10
        self._flac_queue = Queue()
        self._callback = callback

    # SHORT_NORMALIZE = (1.0/32768.0)
    # def get_rms(self, block ):
    #     # RMS amplitude is defined as the square root of the 
    #     # mean over time of the square of the amplitude.
    #     # so we need to convert this string of bytes into 
    #     # a string of 16-bit samples...
    #
    #     # we will get one short out for each 
    #     # two chars in the string.
    #     count = len(block)/2
    #     format = "%dh"%(count)
    #     shorts = unpack(format, block )
    #
    #     # iterate over the block.
    #     sum_squares = 0.0
    #     for sample in shorts:
    #         # sample is a signed short in +/- 32768. 
    #         # normalize it to 1.0
    #         n = sample * self.SHORT_NORMALIZE
    #         sum_squares += n*n
    #     return math.sqrt( sum_squares / count )

    def _is_silent(self, snd_data, sample_data):
        # rms = self.get_rms(snd_data)
        # print rms
        # return rms < self.THRESHOLD
        # return len(snd_data) < self.THRESHOLD
        sample_data = list(sample_data)[0:self.BEGIN_THRESHOLD]
        sample_len = [len(x) for x in sample_data]
        # print len(snd_data), 1.2*sum(sample_len)/len(sample_len)
        return len(snd_data) < 1.2*sum(sample_len)/len(sample_len)

    def _detecting(self):
        while self.keep_running:
            record_begin = False
            buffer_begin = False
            snd_slient_finished = False
            snd_sound_finished = False
            num_silent = 0
            num_sound = 0
            sound_data = ""
            wnd_data = deque(maxlen = 2*self.BEGIN_THRESHOLD)
            sample_data = deque(maxlen = self.BEGIN_THRESHOLD)

            print "detecting:"
            while self.keep_running:
                snd_data = self._flac_queue.get(block=True) #block

                if record_begin:
                    sound_data += snd_data
                else:
                    wnd_data.append(snd_data)

                silent = self._is_silent(snd_data, wnd_data)
                # print len(snd_data), silent
                if silent:
                    num_silent += 1
                    if num_sound < self.BEGIN_THRESHOLD:
                        num_sound = 0
                        snd_sound_finished = False
                    if num_silent > self.TIMEOUT_THRESHOLD:
                        snd_slient_finished = True
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

                self._flac_queue.task_done()
            self._queue.write_data(sound_data)

        print "stop detecting."

    def _flac_write(self, env, buf, samples, current_frame):
        # print current_frame, samples, len(buf)
        if current_frame > 0:
            # print str(self._flac_queue.qsize())
            self._flac_queue.put(buf)
        return True


    def _recording(self):

        # setup the encoder ...
        self.enc = encoder.StreamEncoder()
        self.enc.set_channels(1)
        self.enc.set_sample_rate(self.RATE)
        # initialize
        if self.enc.init_stream(self._flac_write) != encoder.FLAC__STREAM_ENCODER_OK:
            print "flac encode error"

        self._queue = self._queue(self._callback)
        self._queue.start()

        p = pyaudio.PyAudio()
        stream = p.open(format = self.FORMAT,
                    channels = self.CHANNELS,
                    rate = self.RATE,
                    input = True,
                    frames_per_buffer = self.CHUNK_SIZE)

        print "* recording"

        while self.keep_running:
            sound_data = stream.read(self.CHUNK_SIZE)
            self.enc.process(sound_data, self.CHUNK_SIZE)

        print "* done recording"

        # sample_width = p.get_sample_size(self.FORMAT)
        stream.stop_stream()
        stream.close()
        p.terminate()

        self.enc.finish()

    def start_recognizing(self):
        self.keep_running = True

        self._recording_thread = threading.Thread(target=self._recording)
        self._recording_thread.daemon = True
        self._recording_thread.start()

        self._detecting_thread = threading.Thread(target=self._detecting)
        self._detecting_thread.daemon = True
        self._detecting_thread.start()

    def stop_recognizing(self):
        self.keep_running = False # first
        self._queue.stop()

        #self._flac_queue.join()
        print str(self._flac_queue.qsize())
        # self._recording_thread.join()
        # self._detecting_thread.join()


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
            except:
                pass
        # try:
        #     self.__speaking_pipe.stdout.close()
        #     self.__speaking_pipe.stdin.close()
        # except:
        #     pass
        # self.__speaking_pipe = None

    def __speakSpeechFromText(self, phrase):
        googleSpeechURL = self.__getGoogleSpeechURL(phrase)
        subprocess.call(["mpg123", "-q", googleSpeechURL])
        # self.__speaking_pipe = Popen(["mpg123", "-q", googleSpeechURL], stdout=PIPE, stderr=STDOUT, close_fds=True)

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

    def speak(self, phrase):
        print "going to speak:" + phrase
        if not self.__keep_speaking:
            log.warning("__keep_speaking is False.")
            return
            
        if isinstance(phrase, (list, tuple)):
            for item in phrase:
                if isinstance(item, unicode):
                    self.__speak_queue.put(item)
                else:
                    print "phrase must be unicode"
        else:
            if isinstance(phrase, unicode):
                self.__speak_queue.put(phrase)
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
