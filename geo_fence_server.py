#!/usr/bin/ python
# -*- coding: utf-8 -*-

import json
import threading
import Queue
import time
import random

# ----------------------Util

def enum(**enums):
    return type('Enum', (), enums)

# ---------------------- Data

Event = enum(ENTER=0, LEAVE=1, STAY=2)

class GeoResolver:
    def __init__(self, devices):
        self._dev = {}
        for name, device in devices.items(): 
            self._dev[name] = device

    def resolve(self, target_name):
        print "processing loc for %s" % target_name
        print item for item in self._dev.items

    def cal_distance(self, lat1, lan1, lat2, lan2):
        pass

    def notify_state(name, event_type):
        pass

class Device:
    def __init__(self, name):
        self.loc_queue = Queue.Queue(maxsize=15)
        self.name = name

class Location:
    def __init__(self, device, lat, lan):
        self.lat = lat
        self.lan = lan
        self.device = device

# ---------------------- Global

g_loc_queue = Queue.Queue(maxsize=50)
g_devices = {}
g_areas = {}
g_resolver = None

# ----------------------- Logic

def fetch_loc_worker(device, loc_queue):
    print "%s worker thread start." % device.name
    while True:
        rand = random.randint(3,10)

        device.loc_queue.put(Location(device, rand, rand))
        loc_queue.put(device.name)
        loc_queue.task_done()

        print "%s sleep for %d sec" % (device.name, rand)
        time.sleep(rand)

    print "%s worker thread stop." % device.name

def init():
    load_data_from_conf("geo_conf.json")

def load_data_from_conf(path):
    print "load conf:", path
    with open(path) as f:
        conf = json.load(f)

    devices = conf["devices"]
    for name in devices:
        print "load device:", name
        g_devices[name] = Device(name)

def start():
    for name, device in g_devices.items():
        fetch_t = threading.Thread(
                        target=fetch_loc_worker,
                        args=(device, g_loc_queue)
                        )
        fetch_t.daemon = True
        fetch_t.start()

    try:
        g_resolver = GeoResolver(g_devices)
        while True:
            target_name = g_loc_queue.get()
            g_resolver.resolve(target_name)
    except KeyboardInterrupt:
        pass

    print "main thread exit."

def main():
    init()
    start()

if __name__ == "__main__":
    main()
