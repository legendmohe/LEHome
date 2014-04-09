#!usr/bin/env python  
#coding=utf-8  
import subprocess
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

def playmp3(path):
    try:
        with open(path):
            subprocess.Popen(["mpg123", "-q", path])
    except IOError:
        WARN("can't play mp3: " + path)
        pass
