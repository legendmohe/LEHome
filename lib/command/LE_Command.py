#!/usr/bin/env python
# encoding: utf-8

from collections import OrderedDict
from Queue import Queue, Empty
from time import sleep
import threading
import sys

from LE_Command_Parser import LE_Command_Parser
from LEElements import Statement, Block, IfStatement
from lib.sound import LE_Sound
from util.LE_Res import LE_Res


class LE_Command:
    def __init__(self, coms):
        self._registered_callbacks = {}

        self._fsm = LE_Command_Parser(coms)
        self.setDEBUG(False)

        self._fsm.finish_callback = self._finish_callback
        self._fsm.stop_callback = self._stop_callback

        self._keep_running = False

    def _finish_callback(self, block, debug_layer=1):
        if self.DEBUG:
            for statement in block.statements:
                for attr in vars(statement):
                    sys.stdout.write("-"*debug_layer)
                    value = getattr(statement, attr)
                    print "obj.%s = %s" % (attr, value)
                    if isinstance(value, Block):
                        self._finish_callback(value, debug_layer + 1)

        LE_Sound.playmp3(LE_Res.get_res_path("sound/com_begin"))
        t = threading.Thread(
                            target=self._invoke_block,
                            args=(block, )
                            )
        t.daemon = True
        t.start()

    def _stop_callback(self, block, debug_layer=1):
        if self.DEBUG:
            for statement in block.statements:
                for attr in vars(statement):
                    sys.stdout.write("-"*debug_layer)
                    value = getattr(statement, attr)
                    print "obj.%s = %s" % (attr, value)
                    if isinstance(value, Block):
                        self._finish_callback(value, debug_layer + 1)

        LE_Sound.playmp3(LE_Res.get_res_path("sound/com_stop"))
        t = threading.Thread(
                            target=self._invoke_block,
                            args=(block, )
                            )
        t.daemon = True
        t.start()

    def _invoke_block(self, block):
        pass_value = None
        for statement in block.statements:
            if isinstance(statement, Statement):
                coms = OrderedDict([
                    ("delay", statement.delay),
                    ("trigger", statement.trigger),
                    ("action", statement.action),
                    ("target", statement.target),
                    ("stop", statement.stop),
                    ("finish", statement.finish)])
                if pass_value is not None:
                    coms["pass_value"] = pass_value
                msg = statement.msg
                delay_time = statement.delay_time
                pass_value = self._invoke_callbacks(coms, msg, delay_time)
            elif isinstance(statement, IfStatement):
                if self._invoke_block(statement.if_block):
                    self._invoke_block(statement.then_block)
                else:
                    self._invoke_block(statement.else_block)
            elif isinstance(statement, Block):
                pass_value = self._invoke_block(Block)
        return pass_value

    def _invoke_callbacks(self, coms, msg, delay):
        return_value = None
        is_continue = True
        for com_type in coms.keys():
            if not is_continue:
                break
            if coms[com_type] is None or coms[com_type] == "":
                continue
            if not com_type in self._registered_callbacks:
                continue
            callbacks = self._registered_callbacks[com_type]
            if callbacks:
                if coms[com_type] in callbacks:
                    if coms[com_type] is None:
                        continue
                    callback = callbacks[coms[com_type]]
                    if com_type == "delay":
                        is_continue, return_value = callback(
                                delay=delay,
                                action=coms["action"],
                                target=coms["target"],
                                )
                    elif com_type == "trigger":
                        is_continue, return_value = callback(
                                trigger=coms["trigger"],
                                action=coms["action"],
                                pre_value=return_value
                                )
                    elif com_type == "action":
                        is_continue, return_value = callback(
                                action=coms["action"],
                                target=coms["target"],
                                msg=msg,
                                pre_value=return_value
                                )
                    elif com_type == "target":
                        is_continue, return_value = callback(
                                action=coms["action"],
                                target=coms["target"],
                                msg=msg,
                                pre_value=return_value
                                )
                    elif com_type == "stop":
                        is_continue, return_value = callback(
                                action=coms["action"],
                                target=coms["target"],
                                stop=coms["stop"],
                                msg=msg,
                                pre_value=return_value
                                )
                    elif com_type == "finish":
                        is_continue, return_value = callback(
                                action=coms["action"],
                                target=coms["target"],
                                finish=coms["finish"],
                                msg=msg,
                                pre_value=return_value
                                )
                    elif com_type == "nexts":
                        is_continue, return_value = callback(
                                action=coms["action"],
                                target=coms["target"],
                                state=coms["nexts"],
                                msg=msg,
                                pre_value=return_value,
                                pass_value=coms["pass_value"]
                                )

                    if not is_continue:
                        break
        return return_value

    def register_callback(self, com_type, com_item, callback):
        if com_type and com_item and callback:
            if com_type not in self._registered_callbacks:
                self._registered_callbacks[com_type] = {}
            type_coms = self._registered_callbacks[com_type]
            if com_item in type_coms:
                print "warning: " + com_item + ' has registered.'
            type_coms[com_item] = callback
        else:
            print "register_callback: empty args."
            return

    def parse(self, word_stream):
        if not self._keep_running:
            print "invoke start() first."
            return
        for word in list(word_stream):
            self._fsm.put_into_parse_stream(word)

    def start(self):
        self._keep_running = True

    def stop(self):
        self._keep_running = False

    def setDEBUG(self, debug):
        self._fsm.DEBUG = debug
        self.DEBUG = debug


class LE_Comfirmation:
    def __init__(self, rec):
        self._rec = rec

    def confirm(self, ok="ok", cancel="cancel", cfd=0.5):
        print "begin confirmation:ok=%s, cancel=%s, cfd=%f" % (ok, cancel, cfd)

        queue = Queue(1)

        def callback(result, confidence):
            print "confirm: " + result
            if confidence < cfd:
                return
            else:
                try:
                    queue.put(result, timeout=2)
                except Empty:
                    pass

        old_callback = self._rec.queue.callback
        self._rec.queue.callback = callback

        confirmed = False
        for idx in range(5):
            try:
                result = queue.get(timeout=4)
                if result == ok:
                    confirmed = True
                    queue.task_done()
                    break
                elif result == cancel:
                    confirmed = False
                    queue.task_done()
                    break
            except Empty:
                pass

        self._rec.queue.callback = old_callback
        if confirmed:
            return True
        else:
            return False

if __name__ == '__main__':
    def delay_callback(delay=None, action = None, target = None):
        print "* delay callback: %s, action: %s, target: %s" % (delay, action, target)
        return True, "pass"
    def action_callback(action = None, target = None,
            msg=None,
            pre_value=None):
        print "* action callback: %s, target: %s, message: %s pre_value: %s" % (action, target, msg, pre_value)
        return True, "pass"
    def target_callback(
            action=None,
            target = None,
            msg = None, 
            pre_value = None):
        print "* target callback: %s, message: %s pre_value: %s" %(target, msg, pre_value)
        # return False, None
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
    def next_callback(action = None, target = None,
            msg = None, state = None, 
            pre_value = None, pass_value = None):
        print "* next callback: action: %s, target: %s, message: %s state: %s pre_value: %s pass_value %s" %(action, target, msg, state, pre_value, pass_value)
        return True, "pass"

    parser_target = "你好启动如果定时5分钟开灯1那么关门2然后关灯3否则关灯4关门5结束"
    commander = LE_Command({
            "ifs":["如果"],
            "thens":["那么"],
            "elses":["否则"],
            "delay":["定时"],
            "trigger":["启动"],
            "action":["开", "关"],
            "target":["灯", "门"],
            "stop":["停止"],
            "finish":["结束"],
            "nexts":["然后", "接着"],
            })
    commander.setDEBUG(False)
    commander.start()
    
    commander.register_callback("delay", "定时", delay_callback)
    commander.register_callback("action", "开", action_callback)
    commander.register_callback("action", "关", action_callback)
    commander.register_callback("target", "灯", target_callback)
    commander.register_callback("target", "门", target_callback)
    commander.register_callback("stop", "停止", stop_callback)
    commander.register_callback("finish", "结束", finish_callback)
    commander.register_callback("nexts", "然后", next_callback)
    commander.parse(parser_target)
    sleep(5)
    commander.stop()

