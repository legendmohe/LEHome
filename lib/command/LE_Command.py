#!/usr/bin/env python
# encoding: utf-8

from LE_Command_Parser import LE_Command_Parser
from Queue import Queue
from time import sleep
import threading

class LE_Command:
    
    def __init__(self, trigger, action, target, stop, finish, then = None, DEBUG = False):
        self.__registered_callbacks = {}
        
        config = [
            ('trigger' ,trigger),
            ('stop' , stop),
            ('finish' , finish),
            ('action' , action),
            ('target' , target),
            ('then' , then),
            ]
        self.__fsm = LE_Command_Parser(config)
        self.__fsm.DEBUG = DEBUG
        self.__then_flag = then

        self.__fsm.finish_callback = self.__finish_callback
        self.__fsm.stop_callback = self.__stop_callback
        self.__fsm.then_callback = self.__then_callback

        self.__keep_running = False
        self.__work_queues = {}
            

    def __then_callback(self, queue_id, trigger, action, target, message, finish):
        def __worker_thread(work_queue):
            stop = False
            while not stop:
                try:
                    t = work_queue.get(block=True, timeout=2)
                    callback, trigger, action, target, message, finish = t
                    callback(trigger, action, target, message, finish)

                    if finish:
                        print "queue: %d finish" %(queue_id)
                        del self.__work_queues[queue_id]
                        stop = True

                    work_queue.task_done()
                except:
                    pass

        if queue_id not in self.__work_queues.keys():
            work_queue = Queue()

            worker = threading.Thread(target=__worker_thread, args = (work_queue, ))
            worker.daemon = True
            # worker.start()
            self.__work_queues[queue_id] = (worker, work_queue)

        callback = self.__registered_callbacks[action + target]
        if callback:
            worker, work_queue = self.__work_queues[queue_id]
            work_queue.put((callback, trigger, action, target, message, finish))
            if finish:
                worker.start()


    def __finish_callback(self, trigger, action, target, message, finish):
        print action, target
        callback = self.__registered_callbacks[action + target]
        if callback:
            # callback(trigger, action, target, message, finish)
            t = threading.Thread(target=callback, args = (trigger, action, target, message, finish))
            t.daemon = True
            t.start()

    def __stop_callback(self, trigger, action, target, message, finish):
        callback = self.__registered_callbacks[action + target]
        if callback:
            callback(trigger, action, target, message, finish)

    def register_callback(self, command, callback):
        if command and callback:
            if command in self.__registered_callbacks:
                print command + ' has registered.'
            self.__registered_callbacks[command] = callback
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

    def stop(self):
        self.__keep_running = False


if __name__ == '__main__':
    def test_callback(trigger, action, target, message, finish):
        print "* %s >> trigger: %s action: %s, target: %s, message: %s" %(finish, trigger, action, target, message)

    parser_target = "你好启动开灯1结束你好今天天气启动开灯不开停止启动启动结束启动开灯123结束启动关灯结束"
    commander = LE_Command(
            ['启动'],
            ['开', '关'],
            ['灯', '门'],
            ['停止'],
            ['结束'],
            then = ['然后', '接着'],
            DEBUG = False)
    commander.start()
    
    commander.register_callback("开灯", test_callback)
    commander.parse(parser_target)
    sleep(10)
    commander.stop()
