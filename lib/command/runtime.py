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


from collections import OrderedDict
from Queue import Queue, Empty
from types import MethodType
import threading
import sys
import io

from parser import Parser
from lib.model.Elements import Statement, Block, IfStatement, WhileStatement, LogicalOperator, CompareOperator
# from lib.sound import Sound
from util.Res import Res
from util.log import *
from util.thread import StoppableThread


class Rumtime:
    def __init__(self, coms, backup_path="data/backup.pcl"):
        DEBUG("Command __init__.")
        self._lock = threading.Lock()
        self._parse_lock = threading.Lock()
        self._local = threading.local()
        self._thread_lock = threading.Lock()
        self.threads = {}

        self._registered_callbacks = {}
        self._fsm = Parser(coms)
        self.setDEBUG(False)

        self._fsm.finish_callback = self._finish_callback
        self._fsm.stop_callback = self._stop_callback

        self._keep_running = True
        self.backup_path = backup_path

        self._cmd_hook = Rumtime.CommandHook()

    def init_tasklist(self):
        backup_path = self.backup_path
        self._tasklist_path = backup_path
        self._tasklist = []
        tasklist = self._load_tasklist()  # don't self._tasklist
        if not tasklist is None:
            for command in tasklist:
                INFO("exec backup task:%s" % (command, ))
                self._fsm.put_cmd_into_parse_stream(command)

    def _load_tasklist(self):
        with self._lock:
            try:
                with io.open(self._tasklist_path, "r", encoding="utf-8") as f:
                    res = f.read().split()
                    DEBUG("_load_tasklist: %d" % len(res))
                    return res
                    # return Decoder().decode(f)
                    # return json.load(f) #  not loads()
            except Exception, e:
                ERROR(e)
                INFO("no unfinished task list.")
                return []

    def _save_tasklist(self):
        with self._lock:
            DEBUG("_save_tasklist: %d" % len(self._tasklist))
            try:
                with io.open(self._tasklist_path, "w", encoding="utf-8") as f:
                    f.write(u"\n".join(self._tasklist))
                    # f.write(Encoder().encode(self._tasklist))
                    # json.dump(self._tasklist, f)
            except Exception, e:
                ERROR(e)
                ERROR("invaild tasklist path:%s", self._tasklist_path)

    def print_block(self, command, block, index=1):
        print "statements: ", block.statements
        for statement in block.statements:
            sys.stdout.write("-"*index)
            print statement, index
            for attr in vars(statement):
                sys.stdout.write("-"*index)
                block = getattr(statement, attr)
                print "obj.%s = %s" % (attr, block)
                if isinstance(block, Block):
                    self.print_block(command, block, index + 1)

    def _finish_callback(self, command, block):
        # DEBUG(" _finish_callback: %s" % command)
        # self.print_block(command, block)
        # import pdb
        # pdb.set_trace()

        # Sound.play(Res.get_res_path("sound/com_begin"), inqueue=True)
        #  stoppable thread
        t = StoppableThread(
                            target=self._execute,
                            args=(block, command)
                            )
        t.daemon = True
        t.start()

    def _stop_callback(self, command, stop):
        DEBUG(" _stop_callback: %s" % command)
        # Sound.play(Res.get_res_path("sound/com_stop"), inqueue=True)
        if "stop" in self._registered_callbacks:
            callbacks = self._registered_callbacks["stop"]
            if stop in callbacks:
                callbacks[stop](stop=stop)

    def _execute(self, block, command):
        # INFO("start _execute: %s" % command)
        tasklist_item = command
        self._tasklist.append(tasklist_item)
        self._save_tasklist()

        try:
            self.cmd_begin_callback(command)
        except AttributeError:
            DEBUG("no cmd_begin_callback")

        with self._thread_lock:
            if len(self.threads) == 0:
                thread_index = 0
            else:
                thread_index = max([int(key) for key in self.threads.keys()]) + 1
            self.threads[thread_index] = (command, threading.current_thread())
        self._local.cmd = command
        self._local.thread = threading.current_thread()
        self._local.thread.thread_idx = thread_index
        block_stack = Rumtime.BlockStack()
        try:
            DEBUG("begin invoke cmd block: %s", command)
            self._invoke_block(block, block_stack)
            DEBUG("finish invoke cmd block: %s", command)
        except Exception, e:
            EXCEPTION(e)
        del self._local.cmd
        del self._local.thread

        with self._thread_lock:
            del self.threads[thread_index]
            self._tasklist.remove(tasklist_item)
            self._save_tasklist()
        try:
            self.cmd_end_callback(command)
        except AttributeError:
            DEBUG("no cmd_end_callback")

        # INFO("finish _execute: %s" % command)

    def _invoke_block(self, block, stack, pass_value=None, in_loop=False):
        if block is None:
            return None
        # import pdb
        # pdb.set_trace()
        thread = self._local.thread  # break out for thread stopped
        if not in_loop:
            stack.push_context()
        for statement in block.statements:
            if thread.stopped():
                stack.pop_context()
                return False

            if isinstance(statement, Statement):
                pass_value = self._invoke_statement(statement, pass_value, stack)
            elif isinstance(statement, IfStatement):
                if_res = self._invoke_block(statement.if_block, stack, pass_value)
                if if_res is not False and if_res is not None:
                    pass_value = self._invoke_block(statement.then_block, stack, pass_value)
                else:
                    pass_value = self._invoke_block(statement.else_block, stack, pass_value)
            elif isinstance(statement, WhileStatement):
                while True:
                    while_res = self._invoke_block(statement.if_block, stack, pass_value, in_loop=True)
                    if while_res is False or while_res is None:
                        break
                    pass_value = self._invoke_block(statement.then_block, stack, pass_value)
            elif isinstance(statement, CompareOperator):
                bValue = self._invoke_statement(
                                                statement.statement,
                                                pass_value,
                                                stack
                                                )
                pass_value = self._invoke_operator(
                                                    "compare",
                                                    statement.name,
                                                    pass_value,
                                                    bValue,
                                                    stack)
            elif isinstance(statement, LogicalOperator):
                bValue = self._invoke_block(statement.block, stack, pass_value)
                pass_value = self._invoke_operator(
                                                    "logical",
                                                    statement.name,
                                                    pass_value,
                                                    bValue,
                                                    stack)
            elif isinstance(statement, Block):
                pass_value = self._invoke_block(Block, stack, pass_value)
        if not in_loop:
            stack.pop_context()
        return pass_value

    def _invoke_operator(self, otype, name, aValue, bValue, stack):
        if name is None or name == "":
            ERROR("empty %s name." % (otype, ))
            return False
        if not otype in self._registered_callbacks:
            WARN(otype + " callback not registered.")
            return False
        op_callbacks = self._registered_callbacks.get(otype, None)
        if not op_callbacks:
            WARN(otype, " callback is empty.")
            return False
        if not name in op_callbacks:
            WARN("invaild %s name." % (otype, ))
            return False
        callback = op_callbacks[name]
        return callback.internal_callback(
                                        aValue=aValue,
                                        bValue=bValue,
                                        stack=stack
                                        )

    def _invoke_statement(self, statement, pass_value, stack):
        coms = OrderedDict([
            ("trigger", statement.trigger),
            ("nexts", statement.nexts),
            ("whiles", statement.whiles),
            ("if", statement.ifs),
            ("delay", statement.delay),
            ("action", statement.action),
            ("target", statement.target),
            ("finish", statement.finish)])
        coms["pass_value"] = pass_value  # for next token
        coms["stack"] = stack  # for next token
        msg = statement.msg
        delay_time = statement.delay_time

        cmd = statement.action + statement.target + statement.msg
        self._cmd_hook.call_hook_callback(cmd)

        pass_value = self._invoke_callbacks(coms, msg, delay_time)
        return pass_value

    def _invoke_callbacks(self, coms, msg, delay):
        thread = self._local.thread  # break out for thread stopped
        if thread.stopped():
            return

        cmd = self._local.cmd
        pass_value = None
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
                    if com_type == "trigger":
                        return_value = callback.internal_callback(
                                cmd=cmd,
                                trigger=coms["trigger"],
                                action=coms["action"],
                                stack=coms["stack"],
                                )
                        if isinstance(return_value, tuple) and len(return_value) > 1:
                            is_continue = return_value[0]
                            pass_value = return_value[1]
                        elif return_value is None:
                            is_continue = True
                        else:
                            is_continue = return_value
                        if thread.stopped():
                            callback.internal_canceled(
                                    cmd=cmd,
                                    trigger=coms["trigger"],
                                    action=coms["action"],
                                    stack=coms["stack"],
                                    )
                    elif com_type == "nexts":
                        return_value = callback.internal_callback(
                                cmd=cmd,
                                action=coms["action"],
                                target=coms["target"],
                                state=coms["nexts"],
                                msg=msg,
                                pre_value=coms["pass_value"],
                                stack=coms["stack"],
                                )
                        if isinstance(return_value, tuple) and len(return_value) > 1:
                            is_continue = return_value[0]
                            pass_value = return_value[1]
                        elif return_value is None:
                            is_continue = True
                        else:
                            is_continue = return_value
                        if thread.stopped():
                            callback.internal_canceled(
                                    cmd=cmd,
                                    action=coms["action"],
                                    target=coms["target"],
                                    state=coms["nexts"],
                                    msg=msg,
                                    pre_value=coms["pass_value"],
                                    stack=coms["stack"],
                                    )
                    elif com_type == "whiles":
                        return_value = callback.internal_callback(
                                cmd=cmd,
                                whiles=coms["whiles"],
                                msg=msg,
                                action=coms["action"],
                                target=coms["target"],
                                pre_value=pass_value,
                                stack=coms["stack"],
                                )
                        if isinstance(return_value, tuple) and len(return_value) > 1:
                            is_continue = return_value[0]
                            pass_value = return_value[1]
                        elif return_value is None:
                            is_continue = True
                        else:
                            is_continue = return_value
                        if thread.stopped():
                            callback.internal_canceled(
                                    cmd=cmd,
                                    whiles=coms["whiles"],
                                    msg=msg,
                                    action=coms["action"],
                                    target=coms["target"],
                                    pre_value=pass_value,
                                    stack=coms["stack"],
                                    )
                    elif com_type == "if":
                        return_value = callback.internal_callback(
                                cmd=cmd,
                                ifs=coms["if"],
                                msg=msg,
                                action=coms["action"],
                                target=coms["target"],
                                pre_value=pass_value,
                                stack=coms["stack"],
                                )
                        if isinstance(return_value, tuple) and len(return_value) > 1:
                            is_continue = return_value[0]
                            pass_value = return_value[1]
                        elif return_value is None:
                            is_continue = True
                        else:
                            is_continue = return_value
                        if thread.stopped():
                            callback.internal_canceled(
                                    cmd=cmd,
                                    ifs=coms["if"],
                                    msg=msg,
                                    action=coms["action"],
                                    target=coms["target"],
                                    pre_value=pass_value,
                                    stack=coms["stack"],
                                    )
                    elif com_type == "delay":
                        return_value = callback.internal_callback(
                                cmd=cmd,
                                delay=coms["delay"],
                                delay_time=delay,
                                action=coms["action"],
                                target=coms["target"],
                                pre_value=pass_value,
                                stack=coms["stack"],
                                )
                        if isinstance(return_value, tuple) and len(return_value) > 1:
                            is_continue = return_value[0]
                            pass_value = return_value[1]
                        elif return_value is None:
                            is_continue = True
                        else:
                            is_continue = return_value
                        if thread.stopped():
                            callback.internal_canceled(
                                    cmd=cmd,
                                    delay=coms["delay"],
                                    delay_time=delay,
                                    action=coms["action"],
                                    target=coms["target"],
                                    pre_value=pass_value,
                                    stack=coms["stack"],
                                    )
                    elif com_type == "action":
                        return_value = callback.internal_callback(
                                cmd=cmd,
                                action=coms["action"],
                                target=coms["target"],
                                msg=msg,
                                pre_value=pass_value,
                                stack=coms["stack"],
                                )
                        if isinstance(return_value, tuple) and len(return_value) > 1:
                            is_continue = return_value[0]
                            pass_value = return_value[1]
                        elif return_value is None:
                            is_continue = True
                        else:
                            is_continue = return_value
                        if thread.stopped():
                            callback.internal_canceled(
                                    cmd=cmd,
                                    action=coms["action"],
                                    target=coms["target"],
                                    msg=msg,
                                    pre_value=pass_value,
                                    stack=coms["stack"],
                                    )
                    elif com_type == "target":
                        return_value = callback.internal_callback(
                                cmd=cmd,
                                action=coms["action"],
                                target=coms["target"],
                                msg=msg,
                                pre_value=pass_value,
                                stack=coms["stack"],
                                )
                        if isinstance(return_value, tuple) and len(return_value) > 1:
                            is_continue = return_value[0]
                            pass_value = return_value[1]
                        elif return_value is None:
                            is_continue = True
                        else:
                            is_continue = return_value
                        if thread.stopped():
                            callback.internal_canceled(
                                    cmd=cmd,
                                    action=coms["action"],
                                    target=coms["target"],
                                    msg=msg,
                                    pre_value=pass_value,
                                    stack=coms["stack"],
                                    )
                    elif com_type == "finish":
                        return_value = callback.internal_callback(
                                cmd=cmd,
                                action=coms["action"],
                                target=coms["target"],
                                finish=coms["finish"],
                                msg=msg,
                                pre_value=pass_value,
                                stack=coms["stack"],
                                )
                        if isinstance(return_value, tuple) and len(return_value) > 1:
                            is_continue = return_value[0]
                            pass_value = return_value[1]
                        elif return_value is None:
                            is_continue = True
                        else:
                            is_continue = return_value
                        if thread.stopped():
                            callback.internal_canceled(
                                    cmd=cmd,
                                    action=coms["action"],
                                    target=coms["target"],
                                    finish=coms["finish"],
                                    msg=msg,
                                    pre_value=pass_value,
                                    stack=coms["stack"],
                                    )

                    if not is_continue or thread.stopped():
                        break
        return pass_value

    def register_callback(self, com_type, com_item, callback):
        if com_type and com_item and callback:
            if com_type not in self._registered_callbacks:
                self._registered_callbacks[com_type] = {}
            type_coms = self._registered_callbacks[com_type]
            if com_item in type_coms:
                WARN("warning: " + com_item + ' has registered.')
            type_coms[com_item] = callback
        else:
            ERROR("register_callback: empty args.")
            return

    def parse(self, word_stream):
        with self._parse_lock:
            if not self._keep_running:
                WARN("parser is not running.")
                return
            self._fsm.put_into_parse_stream(word_stream)

    def resume_parsing(self):
        self._keep_running = True

    def suspend_parsing(self):
        self._keep_running = False

    def setDEBUG(self, debug):
        self._fsm.DEBUG = debug
        self.DEBUG = debug

    def add_hook(self, cmd):
        if cmd is None or len(cmd) == 0:
            ERROR("add_hook cmd is empty.")
            return
        return self._cmd_hook.add_hook(cmd)


    class CommandHook:
        def __init__(self):
            self._hook_dict = {}

        def add_hook(self, cmd):
            DEBUG("add hook:%s" % cmd)

            if cmd not in self._hook_dict:
                self._hook_dict[cmd] = []

            wait_event = threading.Event()
            event_array = self._hook_dict[cmd]
            event_array.append(wait_event)
            
            # add hook event for stop thread
            current_thread = threading.current_thread()
            if isinstance(current_thread, StoppableThread):
                current_thread.suspend_event = wait_event
            return wait_event

        def call_hook_callback(self, cmd):
            if cmd in self._hook_dict:
                DEBUG("wake hook:%s" % cmd)
                event_array = self._hook_dict[cmd]
                DEBUG("hook size:%d" % len(event_array))
                if len(event_array) != 0:
                    for wait_event in event_array:
                        if not wait_event.isSet():
                            wait_event.set()
                    event_array[:] = []
                del self._hook_dict[cmd]

    class BlockStack:
        def __init__(self):
            self._stack = []
            self._lock = threading.Lock()

        def push_context(self):
            with self._lock:
                self._stack.append({})

        def pop_context(self):
            with self._lock:
                if len(self._stack) > 0:
                    self._stack.pop()

        def cur_layer(self):
            with self._lock:
                return len(self._stack)

        def set_var(self, var_name, value):
            with self._lock:
                if len(self._stack) > 0:
                    self._stack[-1][var_name] = value
                else:
                    ERROR("var_name outside block.")

        def get_value(self, var_name):
            with self._lock:
                if len(self._stack) == 0:
                    return None
                for context in reversed(self._stack):
                    if var_name in context:
                        return context[var_name]
                return None


class Confirmation:
    def __init__(self, home):
        self._home = home

    def confirm(self, ok="ok", cancel="cancel"):
        INFO("begin confirmation:ok=%s, cancel=%s" % (ok, cancel))

        queue = Queue(1)

        # 替换callback
        def callback(self, result):
            if not self._resume:
                INFO("confirm: " + result)
                try:
                    queue.put(result, timeout=2)
                except Empty:
                    pass

        old_callback = self._home.parse_cmd
        self._home.parse_cmd = MethodType(callback, self._home)

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
                else:
                    queue.task_done()
            except Empty:
                pass

        self._home.parse_cmd = old_callback
        if confirmed:
            return True
        else:
            return False


class UserInput:
    def __init__(self, home):
        self._home = home

    def waitForInput(self, finish="finish", cancel="cancel"):
        INFO("begin UserInput.")

        queue = Queue()

        # 替换callback
        def callback(self, result):
            if not self._resume:
                INFO("user input: " + result)
                try:
                    queue.put(result)
                except Empty:
                    pass

        old_callback = self._home.parse_cmd
        self._home.parse_cmd = MethodType(callback, self._home)

        userinput = ""
        while True:
            try:
                content = queue.get()
                queue.task_done()
                if content.endswith(finish):
                    userinput += content[:-len(finish)]
                    break
                elif content.endswith(cancel):
                    userinput = None
                    break
                else:
                    userinput += content
            except Empty:
                pass

        self._home.parse_cmd = old_callback
        return userinput


if __name__ == '__main__':
    from time import sleep

    def delay_callback(delay=None, delay_time = None, action = None, target = None, pre_value = None):
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
    def while_callback(
            whiles=None,
            msg=None,
            action=None,
            target=None,
            pre_value=None
            ):
        return True, "while"

    parser_target = "你好启动重复定时5分钟开灯1那么关门2结束"
    commander = Rumtime({
            "whiles":["循环", "重复"],
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
    commander.resume_parsing()
    
    commander.register_callback("whiles", "重复", while_callback)
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
    commander.suspend_parsing()
