#!/usr/bin/env python
# encoding: utf-8

from LE_Command_Parser import LE_Command_Parser
from Queue import Queue
import threading

class LE_Command:
    
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

        self.__keep_running = False
        self.__worker_queue = Queue()
            
    def __worker_thread(self):
        while self.__keep_running:
            try:
                t = self.__worker_queue.get(block=True, timeout=2)
                callback, trigger, action, target, message, finish = t
                print "\n" + finish + '\n'
                callback(trigger, action, target, message, finish)
                self.__worker_queue.task_done()
            except:
                pass

    def __finish_callback(self, trigger, action, target, message, finish):
        callback, enqueue = self.__registered_callbacks[action + target]
        if callback:
            if enqueue:
                self.__worker_queue.put((callback, trigger, action, target, message, finish))
            else:
                # callback(trigger, action, target, message, finish)
                t = threading.Thread(target=callback, args = (trigger, action, target, message, finish))
                t.daemon = True
                t.start()

    def __stop_callback(self, trigger, action, target, message, finish):
        callback, enqueue = self.__registered_callbacks[action + target]
        if callback:
            callback(trigger, action, target, message, finish)

    def register_callback(self, command, callback, enqueue = False):
        if command and callback:
            if command in self.__registered_callbacks:
                print command + ' has registered.'
            self.__registered_callbacks[command] = (callback, enqueue)
        else:
            return

    def parse(self, word_stream):
        if not self.__keep_running:
            print "invoke start() first."
            return
        for word in list(word_stream):
            self.__fsm.put_into_parse_stream(word)

    def start(self):
        self.__keep_running = True
        self.__worker = threading.Thread(target=self.__worker_thread)
        self.__worker.daemon = True
        self.__worker.start()

    def stop(self):
        if not self.__worker_queue.empty():
            self.__worker_queue.join()
        self.__keep_running = False
        self.__worker.join()

if __name__ == '__main__':
    def test_callback(trigger, action, target, message, finish):
        print "* %s >> trigger: %s action: %s, target: %s, message: %s" %(finish, trigger, action, target, message)

    parser_target = "你好启动开灯1结束你好今天天气启动开灯不开停止启动启动结束启动开灯123结束"
    commander = LE_Command(DEBUG = False)
    commander.start()
    
    commander.register_callback("开灯", test_callback, enqueue = True)
    commander.parse(parser_target)
    commander.stop()
