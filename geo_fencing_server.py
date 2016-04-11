#!/usr/bin/ python
# -*- coding: utf-8 -*-

import json
import threading
import Queue
import collections
import time
import urllib, urllib2
import math
import threading
import random
import os
import signal
import argparse

import tornado.ioloop
import tornado.web
import redis

from util.log import *

# silent mode
INFO = DEBUG

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
        print "resolve!"
        dev = self._dev.get(target_name, None)
        if dev is not None and len(dev.loc_queue) > 1:
            cur_loc = dev.loc_queue[-1]
            last_loc = dev.loc_queue[-2]
            movement = GeoResolver.cal_distance(cur_loc.lat, cur_loc.lon, last_loc.lat, last_loc.lon)
            dev.movements.append(movement)
            # print "movement from", cur_loc.dump(), "to", last_loc.dump(), "is", movement

            intervals = []
            for area_name, area in self._areas.items():
                distance = GeoResolver.cal_distance(cur_loc.lat, cur_loc.lon, area.lat, area.lon)
                INFO("distance from " + str(cur_loc.dump()) + " to " + str(area.dump()) + " is " + str(distance))

                interval = self.cal_interval(dev, distance, self._sensitivity)
                intervals.append(interval)

                if distance <= self._sensitivity and self._area_state[area_name][dev.name] == Event.LEAVE:
                    self.notify_state(area, dev, Event.ENTER)
                    self._area_state[area_name][dev.name] = Event.ENTER
                if distance >= self._sensitivity and self._area_state[area_name][dev.name] == Event.ENTER:
                    self.notify_state(area, dev, Event.LEAVE)
                    self._area_state[area_name][dev.name] = Event.LEAVE

            dev.loc_interval = min(intervals)
            INFO("%s sleep for %f sec, state:%d" % (dev.name, dev.loc_interval, self._area_state[area_name][dev.name]))
            print "%s sleep for %f sec" % (dev.name, dev.loc_interval)

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

    def cal_interval(self, dev, distance, sensitivity):
        # calculation
        interval = 0

        velocity = 0
        clen = len(dev.loc_queue)
        for i in range(1, len(dev.loc_queue)):
            cur_loc = dev.loc_queue[i]
            last_loc = dev.loc_queue[i - 1]
            if (cur_loc.timestamp - last_loc.timestamp != 0):
                velocity += dev.movements[i]*1000/(cur_loc.timestamp - last_loc.timestamp)  # m/s
            else:
                clen -= 1
            print "velocity from", cur_loc.dump(), "to", last_loc.dump(), "velocity", velocity, "interval", (-295*velocity + 210)/0.7
        if clen != 1:
            velocity /= clen - 1

        velocity_interval = 0
        if velocity <= 0.7 and not (self._sensitivity <= distance <= 2*self._sensitivity):
            velocity_interval = (-295*velocity + 210)/0.7
            velocity_interval = velocity_interval if velocity_interval > 0 else 0
            interval += velocity_interval

        distance_interval = 29.5*distance + 5
        interval += distance_interval

        print "interval:", interval, "velocity", velocity, "velocity_interval:", velocity_interval, "distance_interval", distance_interval

        interval = interval if interval > self._min_interval else self._min_interval
        interval = interval if interval < self._max_interval else self._max_interval
        return interval

    def notify_state(self, area, device, event_type):
        print area.name, "notify state", event_type, "for device", device.name
        event = ""
        if event_type == Event.ENTER:
            event = "回到"
        elif event_type == Event.LEAVE:
            event = "离开"

        cmd = "触发#%s%s%s#" % (device.name, event, area.name)
        send_cmd_to_home(cmd)

    def dump(self):
        for name, item in self._dev.items():
            print name, [(loc.lat, loc.lon) for loc in list(item.loc_queue)]


class Device:
    def __init__(self, name, default_interval=15):
        self.loc_queue = collections.deque(maxlen=5)
        self.movements = collections.deque([0], maxlen=self.loc_queue.maxlen)
        self.name = name
        self.loc_interval = default_interval

    def __str__(self):
        return "device:%s" % (self.name, )


class Location:
    def __init__(self, device, lat, lon, ts):
        self.lat = lat
        self.lon = lon
        self.device = device
        self.timestamp = ts

    def dump(self):
        return self.lat, self.lon

    def __str__(self):
        return "%s(%s, %s)" % (self.device, self.lat, self.lon)


class Area:
    def __init__(self, name, lat, lon):
        self.lat = lat
        self.lon = lon
        self.name = name

    def dump(self):
        return self.name, self.lat, self.lon


# ---------------------- Global

g_loc_queue = Queue.Queue(maxsize=25)
g_data_queues = {}
g_devices = {}
g_area = {}
g_wait_locks = {}

g_max_waiting_report = 1*60
g_min_interval = 10
g_max_interval = 15*60
g_sensitivity = 0.05

g_trigger_cmd = "trigger"
g_finish_cmd = "finish"
g_home_address = ""
g_listen_port = 8009
# ----------------------- Logic

class LocationReportHandler(tornado.web.RequestHandler):

    def initialize(self, data_queues):
        self._data_queues = data_queues

    def post(self):
        body = self.request.body
        if body is None or body == "":
            INFO("body is empty")
            self.write("body param is needed")
            return
        try:
            INFO("receive loc report:%s", body)

            datas = body.split("|")
            name = datas[0]
            location_name = datas[1]
            lat = float(datas[2])
            lon = float(datas[3])
            ts = int(datas[4])

            if name.startswith("*"):
                name = name[1:]
            
            data_queue = self._data_queues[name]
            new_loc = Location(name, lat, lon, ts)
            data_queue.put(new_loc)
            data_queue.task_done()
            INFO("put location:%s for %s" % (new_loc, name))
            self.write("ok")
            return
        except Exception, e:
            TRACE_EX()
            ERROR(e)
            INFO("Invalid body:%s" % body)
            self.write("Invalid body.")
            return


class LocationRequestHandler(tornado.web.RequestHandler):
    def get(self):
        name = self.get_argument("name", None)
        if name is None or name == "":
            INFO("name is empty")
            self.write("name param is needed")
            return
        request_for_location(name)


def fetch_loc_worker(device, data_queue, process_queue, wait_lock):
    global g_max_waiting_report

    INFO("%s worker thread start." % device.name)
    process_lock = threading.Event()
    # request first
    send_geo_req_by_home(device)
    # begin geo fencing
    last_st = -1
    while True:  # TODO - will it block here?
        try:
            location = data_queue.get(timeout=g_max_waiting_report)
        except Queue.Empty:
            INFO("report timeout, send another request")
            send_geo_req_by_home(device)
            continue

        if location.timestamp > last_st:  # TODO - seq
            last_st = location.timestamp

            device.loc_queue.append(location)
            process_queue.put((process_lock, device.name))
            process_queue.task_done()
            process_lock.wait()
            process_lock.clear()

            wait_lock.wait(timeout=device.loc_interval)
            wait_lock.clear()

            send_geo_req_by_home(device)

    INFO("%s worker thread stop." % device.name)


def resolver_worker():
    try:
        resolver = GeoResolver(g_devices, g_area, g_min_interval, g_max_interval, g_sensitivity)  # min 10sec, max 15min, sen 200m
        while True:
            lock, target_name = g_loc_queue.get()
            resolver.resolve(target_name)
            lock.set()
    except KeyboardInterrupt:
        pass
    INFO("resolver worker thread exit.")


def init():
    load_data_from_conf("geo_conf.json")
    init_threads()


def load_data_from_conf(path):
    global g_max_interval, g_min_interval, g_sensitivity, g_trigger_cmd, g_finish_cmd, g_home_address

    INFO("load conf:%s" % path)
    with open(path) as f:
        conf = json.load(f)

    devices = conf["devices"]
    for name in devices:
        INFO("load device:%s" % name)
        name = name.encode("utf-8")
        g_devices[name] = Device(name)

    area = conf["area"]
    for name, item in area.items():
        INFO("load area:%s" % name)
        name = name.encode("utf-8")
        g_area[name] = Area(name, item["lat"], item["lon"])

    g_min_interval = conf["min_interval"]
    g_max_interval = conf["max_interval"]
    g_sensitivity = conf["sensitivity"]

    g_trigger_cmd = conf['trigger'].encode("utf-8")
    g_finish_cmd = conf['finish'].encode("utf-8")
    g_home_address = conf['home_address'].encode("utf-8")
    g_listen_port = conf['listen_port']


def request_for_location(name):
    if name in g_wait_locks:
        g_wait_locks[name].set()

def send_cmd_to_home(cmd):
    global g_trigger_cmd, g_finish_cmd, g_home_address

    cmd = "%s%s%s" % (g_trigger_cmd, cmd, g_finish_cmd)
    DEBUG("send cmd %s to home." % (cmd, ))

    try:
        data = {"cmd": cmd}
        enc_data = urllib.urlencode(data)
        response = urllib2.urlopen(g_home_address,
                                    enc_data,
                                    timeout=5).read()
    except urllib2.HTTPError, e:
        ERROR(e)
        return False
    except urllib2.URLError, e:
        ERROR(e)
        return False
    except Exception, e:
        ERROR(e)
        return False
    else:
        INFO("home response: " + response)
        return True

def send_geo_req_by_home(device):
    cmd = "后台定位%s" % device.name
    send_cmd_to_home(cmd)


def init_threads():
    for name, device in g_devices.items():
        wait_lock = threading.Event()
        data_queue = Queue.Queue()
        fetch_t = threading.Thread(
            target=fetch_loc_worker,
            args=(device, data_queue, g_loc_queue, wait_lock)
        )
        fetch_t.daemon = True
        fetch_t.start()

        g_wait_locks[name] = wait_lock
        g_data_queues[name] = data_queue

    resolver_t = threading.Thread(
        target=resolver_worker,
    )
    resolver_t.daemon = True
    resolver_t.start()


def main():
    global g_listen_port

    init()
    application = tornado.web.Application([
        (r"/report", LocationReportHandler, dict(data_queues=g_data_queues)),
        (r"/request", LocationRequestHandler),
    ])
    application.listen(g_listen_port)

    tornado.ioloop.PeriodicCallback(try_exit, 100).start()
    tornado.ioloop.IOLoop.instance().start()


is_closing = False
def signal_handler(signum, frame):
    global is_closing
    is_closing = True


def try_exit():
    global is_closing, mp_context
    if is_closing:
        # clean up here
        tornado.ioloop.IOLoop.instance().stop()

if __name__ == "__main__":
    main()
