#!/usr/bin/ python
# -*- coding: utf-8 -*-

import json
import threading
import Queue
import collections
import time
import math
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
        if dev is not None:
            cur_loc = dev.loc_queue[-1]
            if len(dev.loc_queue) > 1:
                last_loc = dev.loc_queue[-2]
            else:
                last_loc = Location(dev, -1, -1)
            movement = GeoResolver.cal_distance(cur_loc.lat, cur_loc.lon, last_loc.lat, last_loc.lon)
            print "movement from", cur_loc.dump(), "to", last_loc.dump(), "is", movement

            intervals = []
            for area_name, area in self._areas.items():
                distance = GeoResolver.cal_distance(cur_loc.lat, cur_loc.lon, area.lat, area.lon)
                interval = self.cal_interval(movement, distance)
                intervals.append(interval)

                if distance <= self._sensitivity and self._area_state[area_name][dev.name] == Event.LEAVE:
                    self.notify_state(area, dev, Event.ENTER)
                    self._area_state[area_name][dev.name] = Event.ENTER
                if distance >= self._sensitivity and self._area_state[area_name][dev.name] == Event.ENTER:
                    self.notify_state(area, dev, Event.LEAVE)
                    self._area_state[area_name][dev.name] = Event.LEAVE

                print "distance from", cur_loc.dump(), "to", area.dump(), "is", distance
            dev.loc_interval = min(intervals)

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

    def cal_interval(self, movement, distance):
        interval = -1.0

        # calculation

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


# ----------------------- Logic

def fetch_loc_worker(device, loc_queue):
    print "%s worker thread start." % device.name
    while True:
        rand = random.randint(3, 10)

        device.loc_queue.append(Location(device, rand, rand))
        loc_queue.put(device.name)
        loc_queue.task_done()

        print "%s sleep for %d sec" % (device.name, device.loc_interval)
        time.sleep(device.loc_interval)

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
        g_resolver = GeoResolver(g_devices, g_area, 5, 15 * 60, 0.2)
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
