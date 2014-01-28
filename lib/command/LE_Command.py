#!/usr/bin/env python
# encoding: utf-8

from collections import OrderedDict
from Queue import Queue
from time import sleep
import threading

from LE_Command_Parser import LE_Command_Parser
from lib.sound import LE_Sound
from util.LE_Res import LE_Res


class LE_Command:
    def __init__(
            self, trigger, action, target,
            stop, finish, then, DEBUG=False
            ):
        self.__registered_callbacks = {}

        self.__fsm = LE_Command_Parser(
                trigger, action, target,
                stop, finish, then, DEBUG=False
                )
        self.__fsm.DEBUG = DEBUG
        self.__then_flag = then

        self.__fsm.finish_callback = self.__finish_callback
        self.__fsm.stop_callback = self.__stop_callback
        self.__fsm.then_callback = self.__then_callback

        self.__keep_running = False
        self.__work_queues = {}

    def __then_callback(self,
                        queue_id,
                        trigger,
                        action,
                        target,
                        message,
                        state
                        ):
        def __worker_thread(work_queue):
            stop = False
            pass_value = None
            while not stop:
                try:
                    coms, msg, state = work_queue.get(block=True, timeout=1)
                    if pass_value:
                        coms["pass_value"] = pass_value
                    pass_value = self.__invoke_callbacks(coms, msg)

                    if pass_value.lower() == "cancel":
                        print "cancel queue: %d finish" % (queue_id)
                        LE_Sound.playmp3(LE_Res.get_res_path("sound/com_stop"))
                        with work_queue.mutex:
                            work_queue.queue.clear()
                        del self.__work_queues[queue_id]
                        stop = True
                    elif state in self.__registered_callbacks["finish"].keys():
                        print "queue: %d finish" % (queue_id)
                        LE_Sound.playmp3(
                                        LE_Res.get_res_path("sound/com_finish")
                                        )
                        del self.__work_queues[queue_id]
                        stop = True

                    work_queue.task_done()
                except Queue.Empty, ex:
                    pass
                except Exception, ex:
                    print ex

        if trigger == "Error":
            worker, work_queue = self.__work_queues[queue_id]
            with work_queue.mutex:
                work_queue.queue.clear()
            del self.__work_queues[queue_id]
            return

        if queue_id not in self.__work_queues.keys():
            work_queue = Queue()

            worker = threading.Thread(
                    target=__worker_thread,
                    args=(work_queue, )
                    )
            worker.daemon = True
            # worker.start()
            self.__work_queues[queue_id] = (worker, work_queue)

        worker, work_queue = self.__work_queues[queue_id]
        if state in self.__registered_callbacks["finish"].keys():
            worker.start()
        elif state in self.__registered_callbacks["stop"].keys():
            worker, work_queue = self.__work_queues[queue_id]
            with work_queue.mutex:
                work_queue.queue.clear()
            del self.__work_queues[queue_id]
            return

        coms = OrderedDict(
                [("trigger", trigger),
                    ("action", action),
                    ("target", target),
                    ("then", state)]
                )
        work_queue.put((coms, message, state))

    def __finish_callback(self,
            trigger,
            action,
            target,
            message,
            finish):
        LE_Sound.playmp3(LE_Res.get_res_path("sound/com_finish"))

        coms = OrderedDict([
            ("trigger", trigger),
            ("action", action),
            ("target", target),
            ("finish", finish)])
        t = threading.Thread(
                target=self.__invoke_callbacks,
                args=(coms, message))
        t.daemon = True
        t.start()

    def __stop_callback(self, trigger, action, target, message, stop):
        LE_Sound.playmp3(LE_Res.get_res_path("sound/com_stop"))

        coms = [
                ("trigger", trigger),
                ("action", action),
                ("target", target),
                ("stop", stop)
                ]
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
                    if coms[com_type] is None:
                        continue
                    callback = callbacks[coms[com_type]]
                    if com_type == "trigger":
                        is_continue, return_value = callback(
                                trigger=coms["trigger"],
                                action=coms["action"],
                                pre_value=return_value
                                )
                    if com_type == "action":
                        is_continue, return_value = callback(
                                action=coms["action"],
                                target=coms["target"],
                                msg=msg,
                                pre_value=return_value
                                )
                    if com_type == "target":
                        is_continue, return_value = callback(
                                target=coms["target"],
                                msg=msg,
                                pre_value=return_value
                                )
                    if com_type == "stop":
                        is_continue, return_value = callback(
                                action=coms["action"],
                                target=coms["target"],
                                stop=coms["stop"],
                                msg=msg,
                                pre_value=return_value
                                )
                    if com_type == "finish":
                        is_continue, return_value = callback(
                                action=coms["action"],
                                target=coms["target"],
                                finish=coms["finish"],
                                msg=msg,
                                pre_value=return_value
                                )
                    if com_type == "then":
                        is_continue, return_value = callback(
                                action=coms["action"],
                                target=coms["target"],
                                state=coms["then"],
                                msg=msg,
                                pre_value=return_value,
                                pass_value=coms["pass_value"]
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
    def action_callback(action = None, target = None,
            msg=None,
            pre_value=None):
        print "* action callback: %s, target: %s, message: %s pre_value: %s" % (action, target, msg, pre_value)
        return True, "pass"
    def target_callback(target = None,
            msg = None, 
            pre_value = None):
        print "* target callback: %s, message: %s pre_value: %s" %(target, msg, pre_value)
        return True, "pass"
    def stop_callback(action = None, target = None,
            msg = None, stop = None, 
            pre_value = None):
        print "* stop callback: action: %s, target: %s, message: %s stop: %s pre_value: %s" % (action, target, msg, stop, pre_value)
        return True, "pass"

    def finish_callback(action = None, target = None,
            msg = None, finish = None, 
            pre_value = None):
        print "* finish callback: action: %s, target: %s, message: %s finish: %s pre_value: %s" %(action, target, msg, finish, pre_value)
        return True, "pass"
    def then_callback(action = None, target = None,
            msg = None, state = None, 
            pre_value = None, pass_value = None):
        print "* then callback: action: %s, target: %s, message: %s state: %s pre_value: %s pass_value %s" %(action, target, msg, state, pre_value, pass_value)
        return True, "pass"

    parser_target = "你好启动开灯1结束"
    commander = LE_Command(
            trigger = ["启动"],
            action = ["开", "关"],
            target = ["灯", "门"],
            stop = ["停止"],
            finish = ["结束"],
            then = ["然后"],
            DEBUG = False)
    commander.start()
    
    commander.register_callback("action", "开", action_callback)
    commander.register_callback("action", "关", action_callback)
    commander.register_callback("target", "灯", target_callback)
    commander.register_callback("target", "门", target_callback)
    commander.register_callback("stop", "停止", stop_callback)
    commander.register_callback("finish", "结束", finish_callback)
    commander.register_callback("then", "然后", finish_callback)
    commander.parse(parser_target)
    sleep(5)
    commander.stop()
