#!/usr/bin/env python
# encoding: utf-8

#import flac.encoder as encoder
from sys import byteorder
from array import array
from struct import pack

import pyaudio
import wave
import sys,os

import urllib2
import subprocess
import json 
 
import threading

from Queue import Queue, Empty
from time import sleep

class LE_speech_recognizer(object):

    class _queue(object):

        def __init__(self):
            self.write_queue = Queue()
            self.keep_streaming = True

            self.WAVE_OUTPUT_FILENAME = "output.wav"
            self.FLAC_OUTPUT_FILENAME = "output.flac"
            self.RATE = 16000
     
        def start(self):
            self.process_thread = threading.Thread(target=self.process_thread)
            self.process_thread.daemon = True
            self.process_thread.start()
     
        def stop(self):
            print "Waiting write_queue to write all data"
            self.write_queue.join()
            print "Queue empty"
            #sleep(10)
     
            self.keep_streaming=False
            self.write_data(array('h'))
            self.process_thread.join()
     
        def write_data(self, data):
            self.write_queue.put(data)
     
        def gen_data(self):
            if self.keep_streaming:
                (data, sample_width) = self.write_queue.get(block=True) # block!

                wf = wave.open(self.WAVE_OUTPUT_FILENAME, 'wb')
                wf.setnchannels(1)
                wf.setsampwidth(sample_width)
                wf.setframerate(self.RATE)
                wf.writeframes(data)
                wf.close()
                
                cmd = 'flac ' + self.WAVE_OUTPUT_FILENAME + ' -f -o ' + self.FLAC_OUTPUT_FILENAME
                subprocess.call(cmd, stdout=open(os.devnull, "w"), stderr=subprocess.STDOUT)
                os.remove(self.WAVE_OUTPUT_FILENAME)

                flac_data = open(self.FLAC_OUTPUT_FILENAME ,'rb').read()
                return flac_data
   
        def send_and_parse(self, data):
            xurl = 'http://www.google.com/speech-api/v1/recognize?xjerr=1&client=chromium&lang=zh-CN' 
            headers = {'Content-Type' : 'audio/x-flac; rate=16000'}
            req = urllib2.Request(xurl, data, headers)
            response = urllib2.urlopen(req)
            
            strlist = response.read().decode('utf-8')

            #print "strlist" + strlist

            list_data = json.loads(strlist)["hypotheses"]  

            if len(list_data) != 0:
                return list_data[0]["utterance"]

        def process_thread(self):
            while self.keep_streaming:
                try:
                    data = self.gen_data()
                    if self.keep_streaming:
                        result = self.send_and_parse(data)
                        if result is not None:
                            self.callback(result)
                        self.write_queue.task_done()
                except Exception, e:
                    print e
     
            print "end"

    def __init__(self, callback):
        self.keep_running = False
        self._condition = threading.Condition()

        self.CHUNK_SIZE = 512
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000
        self.THRESHOLD = 500

        self._queue = self._queue()
        self._queue.callback = callback
        self._queue.start()

    def _is_silent(self, snd_data):
        return max(snd_data) < self.THRESHOLD

    def _record(self):
        p = pyaudio.PyAudio()
        stream = p.open(format = self.FORMAT,
                    channels = self.CHANNELS,
                    rate = self.RATE,
                    input = True,
                    frames_per_buffer = self.CHUNK_SIZE)

        print "* recording"

        record_begin = False
        buffer_begin = False
        snd_slient_finished = False
        snd_sound_finished = False
        num_silent = 0
        num_sound = 0
        sound_data = array('h')
        buf_data = array('h')

        while self.keep_running:
            # little endian, signed short
            snd_data = array('h', stream.read(self.CHUNK_SIZE))
            if byteorder == 'big':
                snd_data.byteswap()

            if buffer_begin and not record_begin:
                buf_data.extend(snd_data)
            if record_begin:
                sound_data.extend(snd_data)

            silent = self._is_silent(snd_data)
            #print max(snd_data)
            if silent:
                num_silent += 1
                if num_sound <= 5:
                    num_sound = 0
                    snd_sound_finished = False
                if num_silent > 10:
                    buf_data = array('h') # reflash buf
                    buffer_begin = False
                    snd_slient_finished = True
            elif not silent:
                if not buffer_begin:
                    buffer_begin = True
                    buf_data.fromlist([0]*2*self.CHUNK_SIZE)
                    buf_data.extend(snd_data) # first chunk of data

                num_sound += 1
                if num_sound > 5 and num_silent == 0:
                    snd_sound_finished = True
                    
                    if not record_begin:
                        record_begin = True
                        sound_data.extend(buf_data)
                    
                num_silent = 0
                snd_slient_finished = False

            if snd_slient_finished and snd_sound_finished:
                print "data len: " + str(len(sound_data))
                break

        print "* done recording"

        sample_width = p.get_sample_size(self.FORMAT)
        stream.stop_stream()
        stream.close()
        p.terminate()

        return sample_width, sound_data

    def _recognizing(self):
        while self.keep_running:
            sample_width, data = self._record()
            data = pack('<' + ('h'*len(data)), *data)
            if self.keep_running:
                self._queue.write_data((data, sample_width))

    def start_recognizing(self):
        self.keep_running = True
        self._recording_thread = threading.Thread(target=self._recognizing)
        self._recording_thread.daemon = True
        self._recording_thread.start()
        

    def stop_recognizing(self):
        self.keep_running = False # first
        self._queue.stop()

if __name__ == '__main__':
    def callback(result):
        print "result: " + result

    recongizer = LE_speech_recognizer(callback)
    recongizer.start_recognizing()
    sleep(30)
    recongizer.stop_recognizing()
    print "stop."
    while True:
        sleep(0.1)
