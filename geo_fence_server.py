#!/usr/bin/ python
# -*- coding: utf-8 -*-

import json
import threading
import Queue
import collections
import time
import math
import threading
import random


# ----------------------Util

def enum(**enums):
    return type('Enum', (), enums)


# ---------------------- Data

Event = enum(ENTER=0, LEAVE=1)


class GeoResolver:
    def __init__(self, devices, areas, min_interval, max_interval, sensitivity):
        self._dev = {}
        self._area_state = {}
        self._areas = areas
        self._min_interval = min_interval
        self._max_interval = max_interval
        self._sensitivity = sensitivity
        for name, device in devices.items():
            self._dev[name] = device
            for area_name, area in self._areas.items():
                self._area_state[area_name] = {name: Event.LEAVE}

    def resolve(self, target_name):
        # self.dump()
        dev = self._dev.get(target_name, None)
        if dev is not None and len(dev.loc_queue) > 1:
            cur_loc = dev.loc_queue[-1]
            last_loc = dev.loc_queue[-2]
            movement = GeoResolver.cal_distance(cur_loc.lat, cur_loc.lon, last_loc.lat, last_loc.lon)
            dev.movements.append(movement)
            print "movement from", cur_loc.dump(), "to", last_loc.dump(), "is", movement

            intervals = []
            for area_name, area in self._areas.items():
                distance = GeoResolver.cal_distance(cur_loc.lat, cur_loc.lon, area.lat, area.lon)
                print "distance from", cur_loc.dump(), "to", area.dump(), "is", distance
                interval = self.cal_interval(dev, distance)
                intervals.append(interval)

                if distance <= self._sensitivity and self._area_state[area_name][dev.name] == Event.LEAVE:
                    self.notify_state(area, dev, Event.ENTER)
                    self._area_state[area_name][dev.name] = Event.ENTER
                if distance >= self._sensitivity and self._area_state[area_name][dev.name] == Event.ENTER:
                    self.notify_state(area, dev, Event.LEAVE)
                    self._area_state[area_name][dev.name] = Event.LEAVE
                

            dev.loc_interval = min(intervals)
            print "%s sleep for %f sec" % (dev.name, dev.loc_interval)
            print "="*80

    @staticmethod
    def cal_distance(lat1, lon1, lat2, lon2):
        # approximate radius of earth in km
        radius_of_earth = 6373.0

        lat1 = math.radians(lat1)
        lon1 = math.radians(lon1)
        lat2 = math.radians(lat2)
        lon2 = math.radians(lon2)

        dlon = lon2 - lon1
        dlat = lat2 - lat1

        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        distance = radius_of_earth * c
        return distance

    def cal_interval(self, dev, distance):
        # calculation
        avg_movement = sum(dev.movements)/float(len(dev.movements))
        if avg_movement < 0.04 and len(dev.movements) == dev.movements.maxlen: # 40 meters
            interval = (-290.0*avg_movement + 12)/0.04
            print "avg interval:", interval, "avg_movement", avg_movement
        else:
            interval = (290.0*distance + 20.0)/4.9
            print "distance interval:", interval, "distance", distance

        interval = interval if interval > self._min_interval else self._min_interval
        interval = interval if interval < self._max_interval else self._max_interval
        return interval

    def notify_state(self, area, device, event_type):
        print area.name, "notify state", event_type, "for device", device.name

    def dump(self):
        for name, item in self._dev.items():
            print name, [(loc.lat, loc.lon) for loc in list(item.loc_queue)]


class Device:
    def __init__(self, name, default_interval=15):
        self.loc_queue = collections.deque(maxlen=5)
        self.movements = collections.deque(maxlen=self.loc_queue.maxlen)
        self.name = name
        self.loc_interval = default_interval


class Location:
    def __init__(self, device, lat, lon):
        self.lat = lat
        self.lon = lon
        self.device = device

    def dump(self):
        return self.lat, self.lon


class Area:
    def __init__(self, name, lat, lon):
        self.lat = lat
        self.lon = lon
        self.name = name

    def dump(self):
        return self.name, self.lat, self.lon


# ---------------------- Global

g_loc_queue = Queue.Queue(maxsize=25)
g_devices = {}
g_area = {}
g_resolver = None
g_wait_lock = threading.Event()

# ----------------------- Logic

def fetch_loc_worker(device, loc_queue):

    test_loc_data = [
        (23.1210200000, 113.2732000000),
        (23.1178290000, 113.2745660000),
        (23.1147050000, 113.2762900000),
        (23.1104510000, 113.2781590000),
        (23.1071930000, 113.2793810000),
        (23.1049990000, 113.2807460000),
        (23.1018750000, 113.2819680000),
        (23.0984840000, 113.2834770000),
        (23.0967550000, 113.2844110000),
        (23.0967550000, 113.2844110000),
        (23.0967550000, 113.2844110000),
        (23.0967550000, 113.2844110000),
        (23.0967550000, 113.2844110000),
        (23.0928330000, 113.2860640000),
        (23.0928330000, 113.2860640000),
        (23.0848540000, 113.2904480000),
        (23.0821940000, 113.2957660000),
        (23.0798000000, 113.2997900000),
        (23.0777390000, 113.3018020000),
        (23.0777390000, 113.3018020000),
        (23.0777390000, 113.3018020000),
        (23.0777390000, 113.3018020000),
        (23.0777390000, 113.3018020000),
        (23.0773530000, 113.2999740000),
        (23.0781090000, 113.2998130000),
        (23.0782500000, 113.2993540000),
        (23.0780090000, 113.2989230000),
        (23.0777770000, 113.2985640000),
        (23.0779350000, 113.2982410000),
        (23.0781760000, 113.2984340000),
        (23.0782710000, 113.2986670000),
        (23.0782550000, 113.2987620000),
        (23.0782550000, 113.2987620000),
        (23.0782550000, 113.2987620000),
        (23.0782550000, 113.2987620000),
        (23.0782550000, 113.2987620000),
        (23.0782550000, 113.2987620000),
        (23.0782550000, 113.2987620000),
        (23.0782550000, 113.2987620000),
        (23.0782550000, 113.2987620000),
        (23.0782550000, 113.2987620000),
        (23.0782550000, 113.2987620000),
    ]
    test_loc_data.reverse()

    print "%s worker thread start." % device.name
    for test_data in test_loc_data:

        device.loc_queue.append(Location(device, test_data[0], test_data[1]))
        loc_queue.put(device.name)
        loc_queue.task_done()
        # time.sleep(device.loc_interval)
        g_wait_lock.wait(timeout=device.loc_interval)
        g_wait_lock.clear()

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

    area = conf["area"]
    for name, item in area.items():
        print "load area:", name
        g_area[name] = Area(name, item["lat"], item["lon"])


def start():
    for name, device in g_devices.items():
        fetch_t = threading.Thread(
            target=fetch_loc_worker,
            args=(device, g_loc_queue)
        )
        fetch_t.daemon = True
        fetch_t.start()

    try:
        g_resolver = GeoResolver(g_devices, g_area, 10, 15 * 60, 0.2) # min 10sec, max 15min, sen 200m
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
