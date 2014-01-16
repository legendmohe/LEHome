#!/usr/bin/env python
# encoding: utf-8

#import flac.encoder as encoder
from sys import byteorder
from array import array
from struct import pack
import pyaudio
import wave
import sys,os
import requests
import random

import urllib2
import unirest
import json 
 
import threading
from Queue import Queue, Empty
from time import sleep

class speech_recognizer(object):

    class google_stt(object):
        def __init__(self):
            self.write_queue = Queue()
            self._condition = threading.Condition()
            self.keep_streaming = True
     
        def start(self):
            self.process_thread = threading.Thread(target=self.process_thread)
            self.process_thread.start()
     
        def stop(self):
            print "Waiting write_queue to write all data"
            self.write_queue.join()
            print "Queue empty"
            sleep(10)
     
            self.keep_streaming=False
            self.write_data("end")
            self.process_thread.join()
     
        def write_data(self, data):
            with self._condition:
                self.write_queue.put(data)
                self._condition.notify()
     
        def gen_data(self):
            with self._condition:
		while self.write_queue.empty() and self.keep_streaming:
                    print ".waiting."
		    self._condition.wait()

                if not self.write_queue.empty():
                    item = self.write_queue.get()
                    #self.write_queue.task_done()
                    return item
            # while self.keep_streaming:
            #     try:
            #         item = self.write_queue.get(timeout=2)
            #     except Empty:
            #         return
            #     yield item
            #     self.write_queue.task_done()
     
        def process_thread(self):
            while self.keep_streaming:
                try:
                    data = self.gen_data()
                    if self.keep_streaming:
                        result = self.send_and_parse(data)
                        sys.stdout.write("result: " + result)
                except Exception, e:
                    print e
     
            print "end"
            
        def send_and_parse(self, data):
            xurl = 'http://www.google.com/speech-api/v1/recognize?xjerr=1&client=chromium&lang=zh-CN' 
            headers = {'Content-Type' : 'audio/x-flac; rate=16000'}
            req = urllib2.Request(xurl, data, headers)
            response = urllib2.urlopen(req)
            
            strlist = response.read().decode('utf-8')
            list_data = json.loads(strlist)["hypotheses"]  

            result="nono"
            for n in list_data:
               result=n['utterance']     

            return result

    def __init__(self):
        self.keep_running = False
        self._condition = threading.Condition()

        self.CHUNK_SIZE = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000
        self.RECORD_SECONDS = 3
        self.WAVE_OUTPUT_FILENAME = "output.wav"
        self.FLAC_OUTPUT_FILENAME = "output.flac"
        self.THRESHOLD = 500
        self.google_stt = self.google_stt()
        self.google_stt.start()

    def _is_silent(self, snd_data):
        return max(snd_data) < self.THRESHOLD

    def _normalize(self, snd_data):
        "Average the volume out"
        MAXIMUM = 16384
        times = float(MAXIMUM)/max(abs(i) for i in snd_data)

        r = array('h')
        for i in snd_data:
            r.append(int(i*times))
        return r

    def _trim(self, snd_data):
        "Trim the blank spots at the start and end"
        def _itrim(snd_data):
            snd_started = False
            r = array('h')

            for i in snd_data:
                if not snd_started and abs(i) > self.THRESHOLD:
                    snd_started = True
                    r.append(i)

                elif snd_started:
                    r.append(i)
            return r

        # Trim to the left
        snd_data = _itrim(snd_data)

        # Trim to the right
        snd_data.reverse()
        snd_data = _itrim(snd_data)
        snd_data.reverse()
        return snd_data

    def _record(self):
        p = pyaudio.PyAudio()
        stream = p.open(format = self.FORMAT,
                    channels = self.CHANNELS,
                    rate = self.RATE,
                    input = True,
                    frames_per_buffer = self.CHUNK_SIZE)

        print "* recording"

        snd_started = False
        num_silent = 0
        buf = array('h')

        while self.keep_running:
            # little endian, signed short
            snd_data = array('h', stream.read(self.CHUNK_SIZE))
            if byteorder == 'big':
                snd_data.byteswap()
            buf.extend(snd_data)

            silent = self._is_silent(snd_data)
            #print num_silent
            if silent and snd_started:
                num_silent += 1
            elif not silent and snd_started:
                num_silent = 0
            elif not silent and not snd_started:
                snd_started = True

            if snd_started and num_silent > 15:
                break

        print "* done recording"

        sample_width = p.get_sample_size(self.FORMAT)
        stream.stop_stream()
        stream.close()
        p.terminate()
        
        #self._normalize(buf)
        #self._trim(buf)
        return sample_width, buf

    def start_recognizing(self):
        self.keep_running = True
        
        sample_width, data = self._record()
        
        self.flac_thread = threading.Thread(target=self._wav2flac, args=(data, sample_width))
        self.flac_thread.start()

    def _wav2flac(self, data, sample_width):
        #with self._condition:
            data = pack('<' + ('h'*len(data)), *data)

            wf = wave.open(self.WAVE_OUTPUT_FILENAME, 'wb')
            wf.setnchannels(1)
            wf.setsampwidth(sample_width)
            wf.setframerate(self.RATE)
            wf.writeframes(data)
            wf.close()

            cmd = 'flac ' + self.WAVE_OUTPUT_FILENAME + ' -f -o ' + self.FLAC_OUTPUT_FILENAME
            os.system(cmd)
            os.remove(self.WAVE_OUTPUT_FILENAME)

            flac_data = open(self.FLAC_OUTPUT_FILENAME ,'rb').read()

            self.google_stt.write_data(flac_data)

    def stop_recognizing(self):
        self.google_stt.stop()
        self.keep_running = False



if __name__ == '__main__':
    recongizer = speech_recognizer()
    for i in range(9):
        recongizer.start_recognizing()

    recongizer.stop_recognizing()
    print "stop."
