#!/usr/bin/env python
# encoding: utf-8

import re


UTIL_CN_NUM = {
                u'零': 0,
                u'一': 1,
                u'二': 2,
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
                }


def cn2dig(src):
    m = re.match("\d+", src)
    if m:
        return int(m.group(0))
    rsl = 0
    unit = 1
    for item in src[::-1]:
        if item in UTIL_CN_UNIT.keys():
            unit = UTIL_CN_UNIT[item]
        elif item in UTIL_CN_NUM.keys():
            num = UTIL_CN_NUM[item]
            rsl += num*unit
    if rsl < unit:
        rsl += unit
    return int(rsl)


def parse_time(msg):
    m = re.match(ur"([0-9一二三四五六七八九十]*)[点\.]?([0-9一二三四五六七八九十]*)分?", msg)
    if m:
        m1 = cn2dig(m.group(1))
        m2 = cn2dig(m.group(2))
        if m1 == "" and m2 == "":
            return None
        elif m1 != "" and m2 == "":
            return "%d:00" % (m1.zfill(2),)
        elif m1 == "" and m2 != "":
            return str(m2.zfill(2))
        else:
            return "%d:%d" % (m1.zfill(2), m2.zfill(2))
    else:
        return None
