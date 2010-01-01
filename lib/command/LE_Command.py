#!/usr/bin/env python
# encoding: utf-8

from LE_Command_Parser import LE_Command_Parser
from collections import OrderedDict
from Queue import Queue
from time import sleep
import threading

class LE_Command:
    
    def __init__(self, trigger, action, target, stop, finish, then, DEBUG = False):
        self.__registered_callbacks = {}
        
        self.__fsm = LE_Command_Parser(trigger, action, target, stop, finish, then, DEBUG = False)
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
            pass_value = None
            while not stop:
                try:
                    t = work_queue.get(block=True, timeout=1)
                    coms, msg = t
                    if pass_value:
                        coms["pass_value"] = pass_value
                    pass_value = self.__invoke_callbacks(coms, msg)

                    if pass_value == "Error":
                        print "Error in 'then'."
                        with work_queue.mutex:
                            work_queue.queue.clear()
                        del self.__work_queues[queue_id]
                        stop = True
                    elif finish:
                        print "queue: %d finish" %(queue_id)
                        del self.__work_queues[queue_id]
                        stop = True

                    work_queue.task_done()
                except:
                    pass

        if trigger == "Error":
            worker, work_queue = self.__work_queues[queue_id]
            with work_queueq.mutex:
                work_queueq.queue.clear()
            del self.__work_queues[queue_id]
            return 

        if queue_id not in self.__work_queues.keys():
            work_queue = Queue()

            worker = threading.Thread(target=__worker_thread, args = (work_queue, ))
            worker.daemon = True
            # worker.start()
            self.__work_queues[queue_id] = (worker, work_queue)

        worker, work_queue = self.__work_queues[queue_id]
        if finish:
            worker.start()

        coms = OrderedDict([("trigger", trigger), ("action", action), ("target", target), ("then", finish)])
        work_queue.put((coms, message))


    def __finish_callback(self, trigger, action, target, message, finish):
        coms = OrderedDict([("trigger", trigger), ("action", action), ("target", target), ("finish", finish)])
        t = threading.Thread(target=self.__invoke_callbacks, args = (coms, message))
        t.daemon = True
        t.start()

    def __stop_callback(self, trigger, action, target, message, stop):
        coms = [("trigger", trigger), ("action", action), ("target", target), ("stop", stop)]
        self.__invoke_callbacks(OrderedDict(coms), message)

    def __invoke_callbacks(self, coms, msg):
        return_value = None
        is_continue = True
        for com_type in coms.keys():
            if not is_continue:
                break
            if not com_type in self.__registered_callbacks:
                continue
            callbacks = self.__registered_callbacks[com_type]
            if callbacks:
                if coms[com_type] in callbacks:
                    if coms[com_type] == None:
                        continue
                    callback = callbacks[coms[com_type]]
                    if com_type == "trigger":
                        is_continue, return_value = callback(
                                trigger = coms["trigger"],
                                action = coms["action"]
                                )
                    if com_type == "action":
                        is_continue, return_value = callback(
                                action = coms["action"], 
                                target = coms["target"], 
                                msg = msg,
                                pre_value = return_value
                                )
                    if com_type == "target":
                        is_continue, return_value = callback(
                                target = coms["target"], 
                                msg = msg, 
                                pre_value = return_value
                                )
                    if com_type == "stop":
                        is_continue, return_value = callback(
                                action = coms["action"], 
                                target = coms["target"], 
                                stop = coms["stop"],
                                msg = msg, 
                                pre_value = return_value
                                )
                    if com_type == "finish":
                        is_continue, return_value = callback(
                                action = coms["action"], 
                                target = coms["target"], 
                                finish = coms["finish"],
                                msg = msg, 
                                pre_value = return_value
                                )
                    if com_type == "then":
                        is_continue, return_value = callback(
                                action = coms["action"], 
                                target = coms["target"], 
                                then = coms["then"],
                                msg = msg, 
                                pre_value = return_value,
                                pass_value = coms["pass_value"]
                                )

                    if not is_continue:
                        return return_value
        return return_value

    def register_callback(self, com_type, com_item, callback):
        if com_type and com_item and callback:
            if com_type not in self.__registered_callbacks:
                self.__registered_callbacks[com_type] = {}
            type_coms = self.__registered_callbacks[com_type]
            if com_item in type_coms:
                print "warning: " + com_item + ' has registered.'
            type_coms[com_item] = callback
        else:
            print "register_callback: empty args."
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
    def test_callback(trigger = None, action = None, target = None,
            msg = None, stop = None, finish = None, then = None, 
            pre_value = None, pass_value = None):
        print "* trigger: %s action: %s, target: %s, message: %s finish: %s stop: %s then: %s pre_value: %s pass_value %s" %(trigger, action, target, msg, finish, stop, then, pre_value, pass_value)

    parser_target = "你好启动开灯1结束你好今4444abcs,=天天气启动开灯不开停止启动启动结束启动关灯asssdasd然后关门asdasd结束"
    commander = LE_Command(
            trigger = ["启动"],
            action = ["开", "关"],
            target = ["灯", "门"],
            stop = ["停止"],
            finish = ["结束"],
            then = ["然后", "接着"],
            DEBUG = False)
    commander.start()
    
    commander.register_callback("action", "开", test_callback)
    commander.register_callback("action", "关", test_callback)
    commander.register_callback("target", "灯", test_callback)
    commander.register_callback("target", "门", test_callback)
    commander.register_callback("stop", "停止", test_callback)
    commander.register_callback("finish", "结束", test_callback)
    commander.parse(parser_target)
    sleep(5)
    commander.stop()
