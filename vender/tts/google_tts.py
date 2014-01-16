#!/usr/bin/env python
# encoding: utf-8

import flac.encoder as encoder
import pyaudio
import sys
import requests
import random
 
from threading import Thread
from Queue import Queue, Empty
from time import sleep
 
class google_stt_stream(object):
    def __init__(self):
        self.write_queue = Queue()
        self.keep_streaming = True
 
        self.upstream_url = "https://www.google.com/speech-api/full-duplex/v1/up?key=%(key)s&pair=%(pair)s&lang=en-US&maxAlternatives=20&client=chromium&continuous&interim"
        self.upstream_headers = {'content-type': 'audio/x-flac; rate=16000'}
        self.downstream_url = "https://www.google.com/speech-api/full-duplex/v1/down?pair=%(pair)s"
        self.api_key = "AIzaSyBHDrl33hwRp4rMQY0ziRbj8K9LPA6vUCY"
 
    def generate_request_key(self):
        return hex(random.getrandbits(64))[2:-1]
 
    def start(self):
        pair = self.generate_request_key()
        upstream_url = self.upstream_url % {"pair": pair, "key": self.api_key}
        downstream_url = self.downstream_url % {"pair": pair, "key": self.api_key}
 
        self.session = requests.Session()
        self.upstream_thread = Thread(target=self.upstream, args=(upstream_url,))
        self.downstream_thread = Thread(target=self.downstream, args=(downstream_url,))
 
        self.downstream_thread.start()
        self.upstream_thread.start()
 
    def stop(self):
        print "Waiting write_queue to write all data"
        self.write_queue.join()
        print "Queue empty"
        sleep(10)
 
        self.keep_streaming=False
        self.upstream_thread.join()
        self.downstream_thread.join()
 
    def write_data(self, data):
        self.write_queue.put(data)
 
    def gen_data(self):
        while self.keep_streaming:
            try:
                item = self.write_queue.get(timeout=2)
            except Empty:
                return
            yield item
            self.write_queue.task_done()
 
    def upstream(self, url):
        print self.session.post(url, headers=self.upstream_headers, data=self.gen_data())
 
    def downstream(self, url):
        r = self.session.get(url, stream=True)
        while self.keep_streaming:
            try:
                for line in r.iter_content():
                    if not self.keep_streaming:
                        break
                    if line:
                        sys.stdout.write(line)
            except Exception as e:
                print "Exception %s, restarting" %e
                self.keep_streaming = False
                self.upstream_thread.join()
                self.keep_streaming = True
                self.start()
                return
 
        print "end"

if __name__ == '__main__':
        
    stt = google_stt_stream()
     
    def write(enc, buf, samples, current_frame):
        stt.write_data(buf)
        #print current_frame, samples
        return True
     
#config
    chunk = 512
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    THRESHOLD = 180 #The threshold intensity that defines silence signal (lower than).
     
#open stream
    p = pyaudio.PyAudio()
     
    stream = p.open(format = FORMAT,
                    channels = CHANNELS,
                    rate = RATE,
                    input = True,
                    frames_per_buffer = chunk)
     
     
# setup the encoder ...
    enc = encoder.StreamEncoder()
    enc.set_channels(1)
#enc.set_bits_per_sample(wav.getsampwidth()*8)
    enc.set_sample_rate(16000)
#enc.set_compression_level(0)
     
# initialize
    if enc.init_stream(write) != encoder.FLAC__STREAM_ENCODER_OK:
        print "Error"
        sys.exit()
     
# start encoding !
    stt.start()
    nsamples = 512
    while 1:
        data = stream.read(nsamples)
        if not data:
            enc.finish()
            break
        enc.process(data, nsamples)
        #sleep(.001)
     
    stt.stop()
