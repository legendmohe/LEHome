#!usr/bin/env python
#coding=utf-8


import urllib
import urllib2
from util.log import *


def playwav(path):
    import pyaudio  
    import wave  

    chunk = 1024  
    f = wave.open(path, "rb")  
    p = pyaudio.PyAudio()  
    stream = p.open(format = p.get_format_from_width(f.getsampwidth()),  
                            channels = f.getnchannels(),  
                            rate = f.getframerate(),  
                            output = True)  
    data = f.readframes(chunk)  
    while data != '':  
        stream.write(data)  
        data = f.readframes(chunk)  
    stream.stop_stream()  
    stream.close()  
    p.terminate() 


AUDIO_SERVER_ADDRESS = None


def play(path, inqueue=False):
    global AUDIO_SERVER_ADDRESS
    if AUDIO_SERVER_ADDRESS is None:
        WARN("audio server address is empty.")
        return

    values = {'url': path}
    if inqueue:
        values["inqueue"] = True
    data = urllib.urlencode(values)
    url = AUDIO_SERVER_ADDRESS + '/play?' + data
    INFO("sending audio url: " + url)
    try:
        response = urllib2.urlopen(url).read()
    except urllib2.HTTPError, e:
        INFO(e)
        WARN("audio server address is invaild")
    except urllib2.URLError, e:
        INFO(e)
        WARN("audio server unavailable.")
    else:
        INFO("audio response: " + response)
