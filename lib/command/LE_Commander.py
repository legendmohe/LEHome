#!/usr/bin/env python
# encoding: utf-8

from LE_Command_Parser import LE_Command_Parser

class LE_Commander:
    
    def __init__(self, DEBUG = False):
        self.__registered_callbacks = {}
        self.__fsm = LE_Command_Parser([
            ('trigger' ,['启动']),
            ('stop' , ['停止']),
            ('finish' , ['结束']),
            ('action' , ['开']),
            ('target' , ['灯']),
            ])
        self.__fsm.DEBUG = DEBUG
        self.__fsm.finish_callback = self.__finish_callback
        self.__fsm.stop_callback = self.__stop_callback

    def __finish_callback(self, action, target, message):
        command = self.__registered_callbacks[action + target]
        if command:
            command(action, target, message, True)

    def __stop_callback(self, action, target, message):
        command = self.__registered_callbacks[action + target]
        if command:
            command(action, target, message, False)

    def register_callback(self, command, callback):
        if command and callback:
            if command in self.__registered_callbacks:
                print command + ' has registered.'
            self.__registered_callbacks[command] = callback
        else:
            return

    def parse(self, word_stream):
        for word in list(word_stream):
            self.__fsm.put_into_parse_stream(word)

if __name__ == '__main__':
    def test_callback(action, target, message, is_finished):
        print "* %r >> action: %s, target: %s, message: %s" %(is_finished, action, target, message)

    parser_target = "你好启动开灯结束你好今天天气启动开灯不开停止启动启动结束启动开灯123结束"
    commander = LE_Commander(DEBUG = False)
    commander.register_callback("开灯", test_callback)

    commander.parse(parser_target)
