#!/usr/bin/env python
# encoding: utf-8
# Copyright 2014 Xinyu, He <legendmohe@foxmail.com>
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#   http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import re
import datetime
import urllib2
import json
import os
import errno
from HTMLParser import HTMLParser


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise

UTIL_CN_NUM = {
                u'零': 0,
                u'一': 1,
                u'二': 2,
                u'两': 2,
                u'三': 3,
                u'四': 4,
                u'五': 5,
                u'六': 6,
                u'七': 7,
                u'八': 8,
                u'九': 9,
                }
UTIL_CN_UNIT = {
                u'十': 10,
                u'百': 100,
                u'千': 1000,
                u'万': 10000,
                }


def cn2dig(src):
    if src == "":
        return None
    m = re.match("\d+", src)
    if m:
        return m.group(0)
    rsl = 0
    unit = 1
    for item in src[::-1]:
        if item in UTIL_CN_UNIT.keys():
            unit = UTIL_CN_UNIT[item]
        elif item in UTIL_CN_NUM.keys():
            num = UTIL_CN_NUM[item]
            rsl += num*unit
        else:
            return None
    if rsl < unit:
        rsl += unit
    return str(rsl)


def parse_time(msg):
    m = re.match(ur"(([0-9零一二两三四五六七八九十百]+[点:\.])?([0-9零一二三四五六七八九十百]+分)?)", msg)
    if m.group(0):
        m1 = None
        m2 = None
        if m.group(2):
            m1 = m.group(2)
        if m.group(3):
            m2 = m.group(3)

        if m1 is None:
            m2 = cn2dig(m2[:-1])
            return m2.zfill(2)
        elif m2 is None:
            m1 = cn2dig(m1[:-1])
            return "%s:00" % (m1.zfill(2),)
        else:
            m1 = cn2dig(m1[:-1])
            m2 = cn2dig(m2[:-1])
            return "%s:%s" % (m1.zfill(2), m2.zfill(2))
    else:
        return None


def parse_datetime(msg):
    if msg is None or len(msg) == 0:
        return None
    m = re.match(ur"([0-9零一二两三四五六七八九十]+年)?([0-9一二两三四五六七八九十]+月)?([0-9一二两三四五六七八九十]+[号日])?([0-9一二两三四五六七八九十]*[明后大天]+)?([上下午晚早]+)?([0-9零一二两三四五六七八九十百]+[点钟:\.小时整正]+)?([0-9零一二三四五六七八九十百]+分钟?)?([0-9零一二三四五六七八九十百]+秒钟?)?", msg)
    if m.group(0) is not None and len(m.group(0).strip()) != 0:
        res = {
            "year": m.group(1),
            "month": m.group(2),
            "day": m.group(3),
            "hour": m.group(6) if m.group(6) is not None else '00',
            "minute": m.group(7) if m.group(7) is not None else '00',
            "second": m.group(8) if m.group(8) is not None else '00',
            # "microsecond": '00',
            }
        params = {}
        for name in res:
            remove_count = 1
            if res[name] is not None and len(res[name]) != 0:
                if res[name].endswith(u"小时") or \
                   res[name].endswith(u"点正") or \
                   res[name].endswith(u"点整") or \
                   res[name].endswith(u"点钟") or \
                   res[name].endswith(u"秒钟") or \
                   res[name].endswith(u"分钟"):
                    remove_count = 2
                params[name] = int(cn2dig(res[name][:-remove_count]))
        target_date = datetime.datetime.today().replace(**params)
        next_day = m.group(4)
        if next_day is not None:
            day = target_date.date().day
            if next_day == u"明天":
                target_date = target_date.replace(day=day+1)
            elif next_day == u"后天":
                target_date = target_date.replace(day=day+2)
            elif next_day == u"大后天":
                target_date = target_date.replace(day=day+3)
            elif next_day.endswith(u"天后"):
                try:
                    days_after = int(cn2dig(next_day[:-2]))
                    target_date = target_date.replace(day=day+days_after)
                except Exception, ex:
                    return None
            else:
                return None
        is_pm = m.group(5)
        if is_pm is not None:
            if is_pm == u'下午' or is_pm == u'晚上':
                hour = target_date.time().hour
                if hour < 12:
                    target_date = target_date.replace(hour=hour+12)
                return target_date
            elif is_pm == u"上午" or is_pm == u"早上":
                return target_date
            else:
                return None
        return target_date 
    else:
        return None


# def gap_for_timestring(msg):
#     if msg is None or len(msg) == 0:
#         return None
#     t = 0
#     is_pm = False
#     if msg.startswith(u"上午") or msg.startswith(u"早上"):
#         msg = msg[2:]
#     elif msg.startswith(u"下午") or msg.startswith(u"晚上"):
#         is_pm = True
#         msg = msg[2:]
#
#     time_string = parse_time(msg)
#     if time_string is None:
#         return None
#     t_list = time_string.split(":")
#     target_hour = int(t_list[0])
#     if is_pm:
#         target_hour = target_hour + 12
#     target_min = int(t_list[1])
#     now = datetime.datetime.now()
#     cur_hour = now.hour
#     cur_min = now.minute
#     if cur_hour < target_hour or \
#             (cur_hour <= target_hour and cur_min <= target_min):
#         t = t + (target_hour - cur_hour)*60*60 + (target_min - cur_min)*60
#     else:
#         t = t + 24*60*60 - \
#                 ((cur_hour - target_hour)*60*60 + (cur_min - target_min)*60)
#     return t


def gap_for_timestring(msg):
    if msg is None or len(msg) == 0:
        return None
    target = parse_datetime(msg)
    if target is None:
        return None
    now = datetime.datetime.now()
    if now > target:
        target = target + datetime.timedelta(days=1)
    delta = target - now
    return delta.total_seconds()


def wait_for_period(period):
    t1 = period[0]
    t2 = period[1]

    tt1 = gap_for_timestring(t1)
    tt2 = gap_for_timestring(t2)
    
    if tt1 >= tt2:  #draw some graphs to understand this
        return 0
    else:
        return tt1


def var_parse_value(var_value):
    if empty_str(var_value):
        return None
    if var_value.startswith(u'逻辑'):
        if var_value.endswith(u'真'):
            return True
        elif var_value.endswith(u'假'):
            return False
        else:
            return None
    elif var_value.startswith(u'数值'):
        try:
            value = int(var_value[2:])
        except:
            return None
        return value
    elif var_value.startswith(u'字符'):
        try:
            value = unicode(var_value[2:])
        except:
            return None
        return value
    else:
        return None


def xunicode(u):
    if u is None:
        return u''
    else:
        return u

def what_day_is_today():
    return datetime.datetime.today().weekday()

g_workday_cache = None
g_workday_fetched = None
def is_workday_today():
    global g_workday_cache, g_workday_fetched

    check_date =datetime.datetime.today()
    if g_workday_fetched is None or g_workday_fetched.day < check_date.day:
        print "init workday"
        weekday_api = "http://lehome.sinaapp.com/tool/workdaychecker?d=" + check_date.strftime('%Y%m%d')
        try:
            day_type = urllib2.urlopen(weekday_api).read()
            g_workday_cache = int(day_type)
            g_workday_fetched = check_date
            return g_workday_cache
        except Exception, ex:
            print ex
    elif not g_workday_cache is None:
        return g_workday_cache

    if what_day_is_today() > 4:
        return 1
    else:
        return 0

class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return ''.join(self.fed)


def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()


def empty_str(src):
    if src is None or len(src) == 0:
        return True
    return False

if __name__ == "__main__":
    # print parse_time(u"7:30")
    # print parse_time(u"两点30分")
    # print parse_time(u"7点")
    # print parse_time(u"五分")
    # print parse_time(u"一百零五分")
    # print parse_time(u"七点五分")
    # print parse_time(u"七点零五分")
    # print parse_time(u"9点04分")


    # print parse_datetime(u"7点")
    # print parse_datetime(u"五分")
    # print parse_datetime(u"七点五分")
    # print parse_datetime(u"七点零五分")
    # print parse_datetime(u"9点04分")
    # print parse_datetime(u"下午9点04分")
    # print parse_datetime(u"6月三十日04分")
    # print parse_datetime(u"1995年6月10号下午3点41分50秒")
    # print parse_datetime(u"明天下午3点41分50秒")
    # print parse_datetime(u"5天后下午3点41分50秒")
    # print parse_datetime(u"5天后下午3点整")
    # #
    # print gap_for_timestring(u"3月6日下午四点")
    # print parse_datetime(u"7点钟")
    # print gap_for_timestring(u"2秒")
    # print gap_for_timestring(u"5分钟")
    print gap_for_timestring(u"早上8点钟")
    for i in [1]*10:
        print type(is_workday_today())
