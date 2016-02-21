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


import threading
from collections import deque

from fysom import Fysom

from lib.model.Elements import Statement, IfStatement, WhileStatement, Block, LogicalOperator, CompareOperator
from util.log import *


class Parser:

    ESCAPE_BEGIN = u"#"
    ESCAPE_END = u"#"

    _error_occoured = False
    _message_buf = ''
    _delay_buf = ''
    _statement = Statement()
    _block_stack = [Block()]
    _is_cmd_triggered = False
    _last_cmd = ''

    def onfound_delay(self, e):
        DEBUG('event: %s, src: %s, dst: %s' % (e.event, e.src, e.dst))
        if e.dst == "error_state":
            self._error_occoured = True
            return
        if e.dst == "delay_state":
            self._statement.delay = e.args[1]

    def onfound_trigger(self, e):
        DEBUG('event: %s, src: %s, dst: %s' % (e.event, e.src, e.dst))
        if e.dst == "error_state":
            self._error_occoured = True
            return
        if e.src == "initial_state":
            self._last_cmd = ''
            self._is_cmd_triggered = True
            self._lock.acquire()
            self._statement.trigger = e.args[1]

    def onfound_target(self, e):
        DEBUG('event: %s, src: %s, dst: %s' % (e.event, e.src, e.dst))
        if e.dst == "error_state":
            self._error_occoured = True
            return
        if e.dst == "target_state":
            self._statement.target = e.args[1]

    def onfound_action(self, e):
        DEBUG('event: %s, src: %s, dst: %s' % (e.event, e.src, e.dst))
        if e.dst == "error_state":
            self._error_occoured = True
            return
        if e.dst == "action_state":
            self._statement.action = e.args[1]

    def onfound_others(self, e):
        DEBUG('event: %s, src: %s, dst: %s' % (e.event, e.src, e.dst))

        if e.dst == "error_state":
            self._error_occoured = True

    def onfound_finish_flag(self, e):
        DEBUG('event: %s, src: %s, dst: %s' \
                                % (e.event, e.src, e.dst))

        if e.dst == "error_state":
            self._error_occoured = True
            return
        elif e.src in ['action_state', 'target_state', 'message_state']:
            self._statement.finish = e.args[1]
            block = self._block_stack[-1]
            if isinstance(block, Block):
                self._append_statement(block)

            if self.finish_callback:
                self.finish_callback(self._last_cmd, self._block_stack[0])

            self._is_cmd_triggered = False
            self._reset_element()

    def onfound_stop_flag(self, e):
        DEBUG('event: %s, src: %s, dst: %s' % (e.event, e.src, e.dst))
        if e.dst == "error_state":
            self._error_occoured = True
        elif e.src in ['trigger_state',
                        'action_state',
                        'target_state',
                        'message_state',
                        'if_state',
                        'delay_state']:

            self._statement.stop = e.args[1]
            if self.stop_callback:
                self.stop_callback(self._last_cmd, self._statement.stop)

            self._is_cmd_triggered = False
            self._reset_element()

    def onfound_nexts_flag(self, e):
        DEBUG('event: %s, src: %s, dst: %s' % (e.event, e.src, e.dst))
        if e.dst == "error_state":
            self._error_occoured = True
            return

        if e.dst == "trigger_state":
            block = self._block_stack[-1]
            self._append_statement(block)
            self._statement.nexts = e.args[1]

    def onfound_while(self, e):
        DEBUG('event: %s, src: %s, dst: %s' % (e.event, e.src, e.dst))
        if e.dst == "error_state":
            self._error_occoured = True
            return
        elif e.dst == "message_state":
            return

        self._statement.whiles = e.args[1]
        block = self._block_stack[-1]
        if isinstance(block, Block):
            whiles = WhileStatement()
            block.statements.append(whiles)
            self._block_stack.append(whiles)
            self._block_stack.append(whiles.if_block)

    def onfound_if(self, e):
        DEBUG('event: %s, src: %s, dst: %s' % (e.event, e.src, e.dst))

        if e.dst == "error_state":
            self._error_occoured = True
            return
        elif e.dst == "message_state":
            return

        self._statement.ifs = e.args[1]
        block = self._block_stack[-1]
        if isinstance(block, Block):
            ifs = IfStatement()
            block.statements.append(ifs)
            self._block_stack.append(ifs)
            self._block_stack.append(ifs.if_block)
        # elif isinstance(block, IfStatement):
        #     DEBUG('event: %s, src: %s, dst: %s' % (e.event, e.src, e.dst)
        #     DEBUG("if statement can't be nasted."

    def onfound_then(self, e):
        DEBUG('event: %s, src: %s, dst: %s' % (e.event, e.src, e.dst))

        if e.dst == "error_state":
            self._error_occoured = True
            return

        self._statement.thens = e.args[1]
        self._append_statement(self._block_stack[-1])  # add statement to current block
        for index in range(len(self._block_stack)):  #pop until if_block
            block = self._block_stack.pop()
            if isinstance(block, Block):
                if len(self._block_stack) < 1:
                    break
                ifs = self._block_stack[-1]
                if isinstance(ifs, IfStatement) \
                    or isinstance(ifs, WhileStatement):
                    self._block_stack.append(ifs.then_block)
                    return
        ERROR("single then error.")
        self._error_occoured = True

    def onfound_compare(self, e):
        DEBUG('event: %s, src: %s, dst: %s' % (e.event, e.src, e.dst))
        if e.dst == "error_state":
            self._error_occoured = True
            return
        block = self._block_stack[-1]
        if isinstance(block, Block):
            compare_operator = CompareOperator()
            compare_operator.name = e.args[1]
            self._append_statement(block)
            self._statement = compare_operator.statement
            block.statements.append(compare_operator)

    def onfound_logical(self, e):
        DEBUG('event: %s, src: %s, dst: %s' % (e.event, e.src, e.dst))
        if e.dst == "error_state":
            self._error_occoured = True
            return
        block = self._block_stack[-1]
        if isinstance(block, Block):
            logical_operator = LogicalOperator()
            logical_operator.name = e.args[1]
            self._append_statement(block)
            block.statements.append(logical_operator)
            self._block_stack.append(logical_operator.block)

    def onfound_else(self, e):
        DEBUG('event: %s, src: %s, dst: %s' % (e.event, e.src, e.dst))

        if e.dst == "error_state":
            self._error_occoured = True
            return

        self._statement.elses = e.args[1]
        self._append_statement(self._block_stack[-1])  # add statement to current block
        for index in range(len(self._block_stack)):
            block = self._block_stack.pop()
            if isinstance(block, Block):
                if len(self._block_stack) < 1:
                    break
                ifs = self._block_stack[-1]
                if isinstance(ifs, IfStatement):  # while statement has no else
                    self._block_stack.append(ifs.else_block)
                    return
        ERROR("single else error.")
        self._error_occoured = True

    def onreset(self, e):
        DEBUG('event: %s, src: %s, dst: %s' \
                    % (e.event, e.src, e.dst))

        self._last_cmd = ''
        self._is_cmd_triggered = False

    def onerror_state(self, e):
        DEBUG('event: %s, src: %s, dst: %s' \
                    % (e.event, e.src, e.dst))

    def ontrigger_state(self, e):
        DEBUG('event: %s, src: %s, dst: %s' \
                    % (e.event, e.src, e.dst))

    def oninitial_state(self, e):
        DEBUG('event: %s, src: %s, dst: %s' \
                    % (e.event, e.src, e.dst))

    def _append_statement(self, block):
        self._statement.delay_time = self._delay_buf
        self._statement.msg = self._message_buf
        if len(block.statements) == 0:
            block.statements.append(self._statement)
        else:
            if isinstance(block.statements[-1], CompareOperator):
                pass
            else:
                block.statements.append(self._statement)
        self._statement = Statement()

    _FSM = Fysom({
        'initial': 'initial_state',
        #'final': 'initial_state',
        'events': [
                    {'name': 'found_while', 'src': 'initial_state',  'dst': 'initial_state'},
                    {'name': 'found_if', 'src': 'initial_state',  'dst': 'initial_state'},
                    {'name': 'found_then', 'src': 'initial_state',  'dst': 'initial_state'},
                    {'name': 'found_else', 'src': 'initial_state',  'dst': 'initial_state'},
                    {'name': 'found_delay', 'src': 'initial_state',  'dst': 'initial_state'},
                    {'name': 'found_trigger', 'src': 'initial_state',  'dst': 'trigger_state'},
                    {'name': 'found_action', 'src': 'initial_state',  'dst': 'initial_state'},
                    {'name': 'found_target', 'src': 'initial_state',  'dst': 'initial_state'},
                    {'name': 'found_others', 'src': 'initial_state',  'dst': 'initial_state'},
                    {'name': 'found_stop_flag', 'src': 'initial_state',  'dst': 'initial_state'},
                    {'name': 'found_finish_flag', 'src': 'initial_state',  'dst': 'initial_state'},
                    {'name': 'found_nexts_flag', 'src': 'initial_state',  'dst': 'initial_state'},
                    {'name': 'found_compare', 'src': 'initial_state',  'dst': 'initial_state'},
                    {'name': 'found_logical', 'src': 'initial_state',  'dst': 'initial_state'},

                    {'name': 'found_while', 'src': 'trigger_state',  'dst': 'if_state'},
                    {'name': 'found_if', 'src': 'trigger_state',  'dst': 'if_state'},
                    {'name': 'found_then', 'src': 'trigger_state',  'dst': 'error_state'},
                    {'name': 'found_else', 'src': 'trigger_state',  'dst': 'error_state'},
                    {'name': 'found_delay', 'src': 'trigger_state',  'dst': 'delay_state'},
                    {'name': 'found_trigger', 'src': 'trigger_state',  'dst': 'error_state'},
                    {'name': 'found_action', 'src': 'trigger_state',  'dst': 'action_state'},
                    {'name': 'found_target', 'src': 'trigger_state',  'dst': 'error_state'},
                    {'name': 'found_others', 'src': 'trigger_state',  'dst': 'error_state'},
                    {'name': 'found_finish_flag', 'src': 'trigger_state',  'dst': 'error_state'},
                    {'name': 'found_nexts_flag', 'src': 'trigger_state',  'dst': 'error_state'},
                    {'name': 'found_compare', 'src': 'trigger_state',  'dst': 'error_state'},
                    {'name': 'found_logical', 'src': 'trigger_state',  'dst': 'error_state'},

                    {'name': 'found_while', 'src': 'delay_state',  'dst': 'error_state'},
                    {'name': 'found_if', 'src': 'delay_state',  'dst': 'error_state'},
                    {'name': 'found_then', 'src': 'delay_state',  'dst': 'error_state'},
                    {'name': 'found_else', 'src': 'delay_state',  'dst': 'error_state'},
                    {'name': 'found_delay', 'src': 'delay_state',  'dst': 'error_state'},
                    {'name': 'found_trigger', 'src': 'delay_state',  'dst': 'error_state'},
                    {'name': 'found_action', 'src': 'delay_state',  'dst': 'action_state'},
                    {'name': 'found_target', 'src': 'delay_state',  'dst': 'error_state'},
                    {'name': 'found_others', 'src': 'delay_state',  'dst': 'delay_state'},
                    {'name': 'found_finish_flag', 'src': 'delay_state',  'dst': 'error_state'},
                    {'name': 'found_nexts_flag', 'src': 'delay_state',  'dst': 'error_state'},
                    {'name': 'found_compare', 'src': 'delay_state',  'dst': 'error_state'},
                    {'name': 'found_logical', 'src': 'delay_state',  'dst': 'error_state'},

                    {'name': 'found_while', 'src': 'if_state',  'dst': 'error_state'},
                    {'name': 'found_if', 'src': 'if_state',  'dst': 'error_state'},
                    {'name': 'found_then', 'src': 'if_state',  'dst': 'error_state'},
                    {'name': 'found_else', 'src': 'if_state',  'dst': 'error_state'},
                    {'name': 'found_delay', 'src': 'if_state',  'dst': 'delay_state'},
                    {'name': 'found_trigger', 'src': 'if_state',  'dst': 'error_state'},
                    {'name': 'found_action', 'src': 'if_state',  'dst': 'action_state'},
                    {'name': 'found_target', 'src': 'if_state',  'dst': 'error_state'},
                    {'name': 'found_others', 'src': 'if_state',  'dst': 'error_state'},
                    {'name': 'found_finish_flag', 'src': 'if_state',  'dst': 'error_state'},
                    {'name': 'found_nexts_flag', 'src': 'if_state',  'dst': 'error_state'},
                    {'name': 'found_compare', 'src': 'if_state',  'dst': 'error_state'},
                    {'name': 'found_logical', 'src': 'if_state',  'dst': 'error_state'},

                    {'name': 'found_delay', 'src': 'action_state',  'dst': 'message_state'},
                    {'name': 'found_trigger', 'src': 'action_state',  'dst': 'message_state'},
                    {'name': 'found_action', 'src': 'action_state',  'dst': 'message_state'},
                    {'name': 'found_target', 'src': 'action_state',  'dst': 'target_state'},
                    {'name': 'found_others', 'src': 'action_state',  'dst': 'message_state'},

                    {'name': 'found_delay', 'src': 'target_state',  'dst': 'message_state'},
                    {'name': 'found_trigger', 'src': 'target_state',  'dst': 'message_state'},
                    {'name': 'found_action', 'src': 'target_state',  'dst': 'message_state'},
                    {'name': 'found_target', 'src': 'target_state',  'dst': 'message_state'},
                    {'name': 'found_others', 'src': 'target_state',  'dst': 'message_state'},

                    {'name': 'found_delay', 'src': 'message_state',  'dst': 'message_state'},
                    {'name': 'found_trigger', 'src': 'message_state',  'dst': 'message_state'},
                    {'name': 'found_action', 'src': 'message_state',  'dst': 'message_state'},
                    {'name': 'found_target', 'src': 'message_state',  'dst': 'message_state'},
                    {'name': 'found_others', 'src': 'message_state',  'dst': 'message_state'},

                    {'name': 'reset', 'src': ['error_state', 'initial_state', 'trigger_state'],  'dst': 'initial_state'},
                    {'name': 'found_stop_flag',
                        'src': ['trigger_state', 'action_state', 'target_state', 'message_state', 'delay_state', 'if_state'], 
                        'dst': 'initial_state'},
                    {'name': 'found_finish_flag', 
                        'src': ['action_state', 'target_state', 'message_state'], 
                        'dst': 'initial_state'},
                    {'name': 'found_nexts_flag', 
                        'src': ['action_state', 'target_state', 'message_state'], 
                        'dst': 'trigger_state'},
                    {'name': 'found_if', 
                        'src': ['action_state', 'target_state', 'message_state'], 
                        'dst': 'message_state'},
                    {'name': 'found_while', 
                        'src': ['action_state', 'target_state', 'message_state'], 
                        'dst': 'message_state'},
                    {'name': 'found_then', 
                        'src': ['action_state', 'target_state', 'message_state'], 
                        'dst': 'trigger_state'},
                    {'name': 'found_else', 
                        'src': ['action_state', 'target_state', 'message_state'], 
                        'dst': 'trigger_state'},
                    {'name': 'found_compare', 
                        'src': ['action_state', 'target_state', 'message_state'], 
                        'dst': 'trigger_state'},
                    {'name': 'found_logical', 
                        'src': ['action_state', 'target_state', 'message_state'], 
                        'dst': 'trigger_state'},
                    ],
        })

    def __init__(self, coms):
        self.flag = []
        self._lock = threading.Lock()

        flags = ['whiles', 'ifs', 'thens', 'elses', 'delay', 'trigger', 'stop', 'finish',
                'action', 'target', 'nexts', 'logical', 'compare']
        for flag in flags:
            if flag in coms.keys():
                self.flag.append((flag, coms[flag]))

        self.DEBUG = False

        self._FSM.onfound_delay = self.onfound_delay
        self._FSM.onfound_trigger = self.onfound_trigger
        self._FSM.onfound_others = self.onfound_others
        self._FSM.onfound_action = self.onfound_action
        self._FSM.onfound_target = self.onfound_target
        self._FSM.onfound_finish_flag = self.onfound_finish_flag
        self._FSM.onfound_stop_flag = self.onfound_stop_flag
        self._FSM.onfound_nexts_flag = self.onfound_nexts_flag
        self._FSM.onfound_compare = self.onfound_compare
        self._FSM.onfound_logical = self.onfound_logical
        self._FSM.onfound_while = self.onfound_while
        self._FSM.onfound_if = self.onfound_if
        self._FSM.onfound_then = self.onfound_then
        self._FSM.onfound_else = self.onfound_else
        self._FSM.onreset = self.onreset

        self._FSM.ontrigger_state = self.ontrigger_state
        self._FSM.oninitial_state = self.oninitial_state
        self._FSM.onerror_state = self.onerror_state

        self._token_buf = []
        self._match_array = []

        self.finish_callback = None
        self.stop_callback = None

        self._in_escape = False

        self._load_stopwords()

    def _reset(self):
        self._reset_element()
        self._FSM.current = "initial_state"
        del self._token_buf[:]
        del self._match_array[:]

    def _parse_token(self, word, is_others=False):
        self._token_buf.append(word)
        match_str = "".join(self._token_buf)
        no_match = True
        if len(self._match_array) == 0:
            loop_flags = self.flag
        else:
            loop_flags = [x for x in self.flag if x[0] in self._match_array]
        tmp_match_array = self._match_array[:]

        # import pdb; pdb.set_trace()
        for token_tuple in loop_flags: 
            if is_others is True:
                break

            found_match_in_token_flag_array = False # a flag that indicate if all mis-match or not
            token_type = token_tuple[0]

            for token_str in token_tuple[1]:
                if token_str.startswith(match_str):
                    found_match_in_token_flag_array = True #found match
                    no_match = False #for no match in each match token
                    if token_type not in self._match_array:
                        self._match_array.append(token_type)
                        
                    if len(token_str) == len(match_str):
                        # if current match type is on top of heap, that means it has the
                        # highest priority. now it totally match the buf, so we get the 
                        # token type
                        if self._match_array[0] == token_type: 
                            del self._match_array[:]
                            del self._token_buf[:]
                            return match_str, token_type, None #that we found the final type

                    # we found the current buf's token type, so we clean the scene
                    # don't use break here, in case longer mismatch token has same 
                    # prefix with lower weight token 
                    break

            #buf will never match the current token type, so we pop it
            if not found_match_in_token_flag_array and token_type in self._match_array:
                self._match_array.remove(token_type)
        # if nothing match, we have to check if last matchs in _token_buf match
        # any words
        if no_match:
            # DEBUG("no match!: %s" % tmp_match_array)
            if len(tmp_match_array) == 0:
                return self._token_buf.pop(), "others", None
            else:
                loop_flags = [x for x in self.flag if x[0] in tmp_match_array]
                move_back_idx = 0
                while move_back_idx <= len(self._token_buf):
                    move_back_idx += 1
                    match_str = "".join(self._token_buf[:-move_back_idx])
                    move_back_array = self._token_buf[-move_back_idx:]
                    for token_tuple in loop_flags: 
                        token_type = token_tuple[0]
                        for token_str in token_tuple[1]:
                            if token_str == match_str: 
                                del self._match_array[:]
                                del self._token_buf[:]
                                # DEBUG("match!: %s %s" % (match_str, move_back_array))
                                return match_str, token_type, move_back_array

                first_char = self._token_buf[0]
                move_back_array = self._token_buf[1:]
                del self._match_array[:]
                del self._token_buf[:]
                # DEBUG("rollback...........")
                return first_char, "others", move_back_array

        return None, None, None

    def put_cmd_into_parse_stream(self, cmd):
        trigger = self.flag[5]
        if trigger[0] == "trigger":
            cmd = trigger[1][0] + cmd
        else :
            ERROR("put_cmd_into_parse_stream has no trigger words")
            return
        finish = self.flag[7]
        if finish[0] == "finish":
            cmd = cmd + finish[1][0]
        else :
            ERROR("put_cmd_into_parse_stream has no finish words")
            return
        self.put_into_parse_stream(cmd)

    def put_into_parse_stream(self, stream_term):
        # if self.DEBUG :
        DEBUG("put[%s] into parse stream." %(stream_term, ))
        # import pdb; pdb.set_trace()
        parse_chars = deque(stream_term)
        while len(parse_chars) != 0:
            a_char = parse_chars.popleft()
            # DEBUG("parse_chars:%s" % parse_chars)
            # escape for confilct chars
            if not self._in_escape is True and a_char == Parser.ESCAPE_BEGIN:
                self._in_escape = True
                self._last_cmd += a_char
                continue
            elif self._in_escape is True and a_char == Parser.ESCAPE_END:
                self._in_escape = False
                self._last_cmd += a_char
                continue
            elif not self._in_escape and \
                    (a_char.isspace() or a_char in self._stopwords):
                INFO(u"ignore:" + a_char)
                continue

            # DEBUG("got a_char:%s" % a_char)
            token, token_type, rollback = self._parse_token(a_char, is_others=self._in_escape)
            if rollback is not None:
                # current token is not current char but the last matching token
                # so we need to push it in front of parse_chars
                parse_chars.extendleft(reversed(rollback))
            if token is None:
                continue

            DEBUG("parse token:%s type:%s" % (token, token_type))
            if token_type == "whiles":
                self._FSM.found_while(self, token)
                if not self._FSM.current == "message_state":
                    self._message_buf = ''
                    self._delay_buf = ''
            elif token_type == "ifs":
                self._FSM.found_if(self, token)
                if not self._FSM.current == "message_state":
                    self._message_buf = ''
                    self._delay_buf = ''
            elif token_type == "thens":
                self._FSM.found_then(self, token)
                self._message_buf = ''
                self._delay_buf = ''
            elif token_type == "elses":
                self._FSM.found_else(self, token)
                self._message_buf = ''
                self._delay_buf = ''
            elif token_type == "delay":
                self._FSM.found_delay(self, token)
            elif token_type == "trigger":
                self._FSM.found_trigger(self, token)
            elif token_type == "action":
                self._FSM.found_action(self, token)
            elif token_type == "target":
                self._FSM.found_target(self, token)
            elif token_type == "stop":
                self._FSM.found_stop_flag(self, token)
                self._message_buf = ''
                self._delay_buf = ''
            elif token_type == "finish":
                self._FSM.found_finish_flag(self, token)
                self._message_buf = ''
                self._delay_buf = ''
            elif token_type == "nexts":
                self._FSM.found_nexts_flag(self, token)
                self._message_buf = ''
                self._delay_buf = ''
            elif token_type == "compare":
                self._FSM.found_compare(self, token)
                self._message_buf = ''
                self._delay_buf = ''
            elif token_type == "logical":
                self._FSM.found_logical(self, token)
                self._message_buf = ''
                self._delay_buf = ''
            elif token_type == "others":
                self._FSM.found_others(self, token)
                if self._FSM.current == 'delay_state':  # put it into buf here
                    self._delay_buf += token

            if self._FSM.current == 'message_state':
                self._message_buf += token
            if self._is_cmd_triggered and not token_type == "trigger":
                self._last_cmd += token

            if self._error_occoured:
                self._FSM.reset()
                self._reset_element()
                self._error_occoured = False
        DEBUG("exit parse current stream:%s", stream_term)

    def last_command(self):
        return self._last_cmd

    def _reset_element(self):
        self._statement = Statement()
        self._block_stack = [Block()]
        if self._lock.locked():
            self._lock.release()

    def reset(self):
        self._reset()

    def _load_stopwords(self):
        self._stopwords = set()
        with open('usr/stopwords.txt') as stopwords:
            for word in stopwords.readlines():
                self._stopwords.add(word.strip().decode('utf-8'))

if __name__ == '__main__':

    def test_callback(command, block, index=1):
        import sys
        print block.statements
        for statement in block.statements:
            for attr in vars(statement):
                sys.stdout.write("-"*index)
                block = getattr(statement, attr)
                print "obj.%s = %s" % (attr, block)
                if isinstance(block, Block):
                    test_callback(command, block, index + 1)

    def stop_callback(command, stop):
        print command, stop

    fsm = Parser({
            "whiles":["循环", "重复"],
            "ifs":["如果"],
            "thens":["那么"],
            "elses":["否则"],
            "delay":["定时"],
            "trigger":["启动"],
            "action":["开", "关", "执行"],
            "target":["灯", "门"],
            "stop":["停止"],
            "finish":["结束"],
            "nexts":["然后", "接着"],
            "logical":["等于"],
            })
    fsm.DEBUG = True
    fsm.finish_callback = test_callback
    fsm.stop_callback = stop_callback
    #TODO - "不要停&停止"
    parser_target = "启动开灯结束"
    fsm.put_into_parse_stream(parser_target)
    print fsm.last_command()
    parser_target = "启动如果开灯等于关灯那么开门谢谢"
    fsm.put_into_parse_stream(parser_target)
    print fsm.last_command()

