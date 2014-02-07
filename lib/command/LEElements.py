#!/usr/bin/env python
# encoding: utf-8


class Statement:
    def __init__(self):
        self.delay = ""
        self.delay_time = ""
        self.trigger = ""
        self.action = ""
        self.target = ""
        self.msg = ""
        self.stop = ""
        self.finish = ""
        self.ifs = ""
        self.thens = ""
        self.elses = ""
        self.whiles = ""


class Block:
    def __init__(self):
        self.statements = []


class IfStatement:
    def __init__(self):
        self.if_block = Block()
        self.then_block = Block()
        self.else_block = Block()


class WhileStatement:
    def __init__(self):
        self.if_block = Block()
        self.then_block = Block()
