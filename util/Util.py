#!/usr/bin/env python
# encoding: utf-8

import re


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
        return ""
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


def empty_str(src):
    if src is None or len(src) == 0:
        return True
    return False

if __name__ == "__main__":
    print parse_time(u"7:30")
    print parse_time(u"两点30分")
    print parse_time(u"7点")
    print parse_time(u"五分")
    print parse_time(u"一百零五分")
    print parse_time(u"七点五分")
    print parse_time(u"七点零五分")
    print parse_time(u"9点04分")
