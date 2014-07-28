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

import sys


class Statement:
    def __init__(self):
        self.delay = ""
        self.delay_time = ""
        self.trigger = ""
        self.nexts = ""
        self.action = ""
        self.target = ""
        self.msg = ""
        self.stop = ""
        self.finish = ""
        self.ifs = ""
        self.thens = ""
        self.elses = ""
        self.whiles = ""

    def __str__(self):
        res = u""
        for attr in vars(self):
            ele = getattr(self, attr)
            res += u"self.%s = %s\n" % (attr, ele)
        sys.stdout.flush()
        return res.encode('utf-8')


class Block:
    def __init__(self):
        self.statements = []

    def __str__(self):
        res = "block:\n"
        for statement in self.statements:
            res += str(statement) + '\n  '
        res += '---block end.\n'
        return res


class LogicalOperator:
    def __init__(self):
        self.name = ""
        self.block = Block()

    def __str__(self):
        res = 'LogicalOperator: ' + self.name.encode('utf-8') + '\n'
        res += str(self.block)
        return res


class CompareOperator:
    def __init__(self):
        self.name = ""
        self.statement = Statement()

    def __str__(self):
        res = 'CompareOperator: ' + self.name.encode('utf-8') + '\n'
        res += str(self.statement)
        return res


class IfStatement:
    def __init__(self):
        self.if_block = Block()
        self.then_block = Block()
        self.else_block = Block()

    def __str__(self):
        res = 'IfStatement: \n'
        res += str(self.if_block) + '\n'
        res += '---then:\n'
        res += str(self.then_block) + '\n'
        res += '---else:\n'
        res += str(self.else_block) + '\n'
        res += '---end if\n'
        return res


class WhileStatement:
    def __init__(self):
        self.if_block = Block()
        self.then_block = Block()

    def __str__(self):
        res = 'WhileStatement: \n'
        res += str(self.if_block) + '\n'
        res += str(self.then_block) + '\n'
        return res
