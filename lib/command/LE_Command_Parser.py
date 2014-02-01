#!/usr/bin/env python
# encoding: utf-8

from fysom import Fysom
from heapq import heappush, heapify
import time

class LE_Command_Parser:

    _error_occoured = False
    _message_buf = ''
    _delay_buf = ''
    _unit_map = {
            'delay':"",
            'finish':"",
            'stop':"",
            'then' :"",
            'trigger':"",
            'action':"",
            'target':"",
            }

    _finish_succeed = False
    _stop_succeed = False
    _then_succeed = False
    _then_queue_id = -1

    def onfound_delay(self, e):
        if self.DEBUG:
            print 'event: %s, src: %s, dst: %s' % (e.event, e.src, e.dst)
        self._unit_map['delay'] = e.args[1]

        if e.dst == "error_state":
            self._error_occoured = True

    def onfound_trigger(self, e):
        if self.DEBUG:
            print 'event: %s, src: %s, dst: %s' % (e.event, e.src, e.dst)
        self._unit_map['trigger'] = e.args[1]
        
        if e.dst == "error_state":
            self._error_occoured = True

    def onfound_target(self, e):
        if self.DEBUG:
            print 'event: %s, src: %s, dst: %s' % (e.event, e.src, e.dst)
        self._unit_map['target'] = e.args[1]
        
        if e.dst == "error_state":
            self._error_occoured = True

    def onfound_action(self, e):
        if self.DEBUG:
            print 'event: %s, src: %s, dst: %s' % (e.event, e.src, e.dst)
        self._unit_map['action'] = e.args[1]

        if e.dst == "error_state":
            self._error_occoured = True

    def onfound_else(self, e):
        if self.DEBUG:
            print 'event: %s, src: %s, dst: %s' % (e.event, e.src, e.dst)

        if e.dst == "error_state":
            self._error_occoured = True

    def onfound_finish_flag(self, e):
        if self.DEBUG:
            print 'finish ! = event: %s, src: %s, dst: %s' % (e.event, e.src, e.dst)

        self._unit_map['finish'] = e.args[1]
        self._finish_succeed = True

        if e.dst == "error_state":
            self._error_occoured = True

    def onfound_stop_flag(self, e):
        if self.DEBUG:
            print 'event: %s, src: %s, dst: %s' % (e.event, e.src, e.dst)

        self._unit_map['stop'] = e.args[1]
        self._stop_succeed = True

        if e.dst == "error_state":
            self._error_occoured = True

    def onfound_then_flag(self, e):
        if self.DEBUG:
            print 'event: %s, src: %s, dst: %s' % (e.event, e.src, e.dst)

        self._unit_map['then'] = e.args[1]
        self._then_succeed = True
        if self._then_queue_id == -1:
            self._then_queue_id = int(time.time())

        if e.dst == "error_state":
            self._error_occoured = True

    def onreset(self, e):
        if self.DEBUG:
            print 'reset ! = event: %s, src: %s, dst: %s' % (e.event, e.src, e.dst)

        self._error_occoured = False

        if e.dst == "error_state":
            self._error_occoured = True

    _FSM = Fysom({
        'initial': 'initial_state',
        #'final': 'initial_state',
        'events': [
                    {'name': 'found_delay', 'src': 'initial_state',  'dst': 'initial_state'},
                    {'name': 'found_trigger', 'src': 'initial_state',  'dst': 'trigger_state'},
                    {'name': 'found_action', 'src': 'initial_state',  'dst': 'initial_state'},
                    {'name': 'found_target', 'src': 'initial_state',  'dst': 'initial_state'},
                    {'name': 'found_else', 'src': 'initial_state',  'dst': 'initial_state'},
                    {'name': 'found_stop_flag', 'src': 'initial_state',  'dst': 'initial_state'},
                    {'name': 'found_finish_flag', 'src': 'initial_state',  'dst': 'initial_state'},
                    {'name': 'found_then_flag', 'src': 'initial_state',  'dst': 'initial_state'},

                    {'name': 'found_delay', 'src': 'delay_state',  'dst': 'error_state'},
                    {'name': 'found_trigger', 'src': 'delay_state',  'dst': 'error_state'},
                    {'name': 'found_action', 'src': 'delay_state',  'dst': 'action_state'},
                    {'name': 'found_target', 'src': 'delay_state',  'dst': 'error_state'},
                    {'name': 'found_else', 'src': 'delay_state',  'dst': 'delay_state'},
                    {'name': 'found_finish_flag', 'src': 'delay_state',  'dst': 'error_state'},
                    {'name': 'found_then_flag', 'src': 'delay_state',  'dst': 'error_state'},

                    {'name': 'found_delay', 'src': 'trigger_state',  'dst': 'delay_state'},
                    {'name': 'found_trigger', 'src': 'trigger_state',  'dst': 'trigger_state'},
                    {'name': 'found_action', 'src': 'trigger_state',  'dst': 'action_state'},
                    {'name': 'found_target', 'src': 'trigger_state',  'dst': 'error_state'},
                    {'name': 'found_else', 'src': 'trigger_state',  'dst': 'error_state'},
                    {'name': 'found_finish_flag', 'src': 'trigger_state',  'dst': 'initial_state'},
                    {'name': 'found_then_flag', 'src': 'trigger_state',  'dst': 'error_state'},

                    {'name': 'found_delay', 'src': 'action_state',  'dst': 'message_state'},
                    {'name': 'found_trigger', 'src': 'action_state',  'dst': 'message_state'},
                    {'name': 'found_action', 'src': 'action_state',  'dst': 'message_state'},
                    {'name': 'found_target', 'src': 'action_state',  'dst': 'target_state'},
                    {'name': 'found_else', 'src': 'action_state',  'dst': 'message_state'},

                    {'name': 'found_delay', 'src': 'target_state',  'dst': 'message_state'},
                    {'name': 'found_trigger', 'src': 'target_state',  'dst': 'message_state'},
                    {'name': 'found_action', 'src': 'target_state',  'dst': 'message_state'},
                    {'name': 'found_target', 'src': 'target_state',  'dst': 'message_state'},
                    {'name': 'found_else', 'src': 'target_state',  'dst': 'message_state'},

                    {'name': 'found_delay', 'src': 'message_state',  'dst': 'message_state'},
                    {'name': 'found_trigger', 'src': 'message_state',  'dst': 'message_state'},
                    {'name': 'found_action', 'src': 'message_state',  'dst': 'message_state'},
                    {'name': 'found_target', 'src': 'message_state',  'dst': 'message_state'},
                    {'name': 'found_else', 'src': 'message_state',  'dst': 'message_state'},

                    {'name': 'found_delay', 'src': 'message_state',  'dst': 'message_state'},
                    {'name': 'found_trigger', 'src': 'message_state',  'dst': 'message_state'},
                    {'name': 'found_action', 'src': 'message_state',  'dst': 'message_state'},
                    {'name': 'found_target', 'src': 'message_state',  'dst': 'message_state'},
                    {'name': 'found_else', 'src': 'message_state',  'dst': 'message_state'},

                    {'name': 'reset', 'src': 'error_state',  'dst': 'initial_state'},
                    {'name': 'found_stop_flag',
                        'src': ['trigger_state', 'action_state', 'target_state', 'message_state', 'delay_state'], 
                        'dst': 'initial_state'},
                    {'name': 'found_finish_flag', 
                        'src': ['action_state', 'target_state', 'message_state'], 
                        'dst': 'initial_state'},
                    {'name': 'found_then_flag', 
                        'src': ['action_state', 'target_state', 'message_state'], 
                        'dst': 'trigger_state'},
                    ],
        }
        )

    def __init__(self, delay, trigger, action, target, stop, finish, then, DEBUG = False):
        self.FLAG = [
            ('delay' , delay),
            ('trigger' , trigger),
            ('stop' , stop),
            ('finish' , finish),
            ('action' , action),
            ('target' , target),
            ('then' , then),
            ]

        self.DEBUG = DEBUG

        self._FSM.onfound_delay = self.onfound_delay
        self._FSM.onfound_trigger = self.onfound_trigger
        self._FSM.onfound_else = self.onfound_else
        self._FSM.onfound_action = self.onfound_action
        self._FSM.onfound_target = self.onfound_target
        self._FSM.onfound_finish_flag = self.onfound_finish_flag
        self._FSM.onfound_stop_flag = self.onfound_stop_flag
        self._FSM.onfound_then_flag = self.onfound_then_flag
        self._FSM.onreset = self.onreset

        self._token_buf = []
        self._match_stack = []

        self.finish_callback = None
        self.stop_callback = None
        self.then_callback = None

    def _reset(self):
        self._reset_unit()
        self._FSM.current = "initial_state"
        del self._token_buf[:]
        del self._match_stack[:]

    def _parse_token(self, word):
        # word = word.encode("utf-8")
        # print word, type(word)
        self._token_buf.append(word)
        _temp_str = "".join(self._token_buf)
        _no_match = True
        _index = 1
        for token_tuple in self.FLAG: 
            _found_match_in_token_flag_array = False # a flag that indicate if all mis-match or not
            _token_type = (_index, token_tuple[0]) #item in heap is tuple (index, item)

            for match_str in token_tuple[1]:
                if match_str.startswith(_temp_str):
                    _found_match_in_token_flag_array = True #found match
                    _no_match = False #for no match in each match token
                    if _token_type not in self._match_stack:
                        heappush(self._match_stack, _token_type) # use heap
                        
                    if len(match_str) == len(_temp_str):
                        # if current match type is on top of heap, that means it has the
                        # highest priority. now it totally match the buf, so we get the 
                        # token type
                        if self._match_stack[0] == _token_type: 
                            del self._match_stack[:]
                            del self._token_buf[:]
                            return _temp_str, _token_type[1] #that we found the final type

                    # we found the current buf's token type, so we clean the scene
                    break

                # in case that token has shorter token length then the buf
                elif _temp_str.startswith(match_str):
                    _found_match_in_token_flag_array = True
                    _no_match = False
                    if _token_type not in self._match_stack:
                        heappush(self._match_stack, _token_type)

                    # in case that lower token has short lengh, and it match
                    if self._match_stack[0] == _token_type:
                        del self._match_stack[:]
                        del self._token_buf[0:len(match_str)] #r
                        return _temp_str, _token_type[1]
                    break

            #buf will never match the current token type, so we pop it
            if not _found_match_in_token_flag_array and _token_type in self._match_stack:
                self._match_stack.remove(_token_type)
                heapify(self._match_stack)

            _index += 1

        if _no_match:
            return self._token_buf.pop(0), "Else"

        return None, None
                
    def put_into_parse_stream(self, stream_term):

        if self.DEBUG :
            print "parse: %s" %(stream_term)

        for item in list(stream_term):
            _token, _token_type = self._parse_token(item)
            if _token == None:
                #print "continue"
                continue
            if _token_type == "delay":
                self._FSM.found_delay(self, _token)
            elif _token_type == "trigger":
                self._FSM.found_trigger(self, _token)
            elif _token_type == "action":
                self._FSM.found_action(self, _token)
            elif _token_type == "target":
                self._FSM.found_target(self, _token)
            elif _token_type == "stop":
                self._FSM.found_stop_flag(self, _token)
                if self._stop_succeed:
                    if self._then_queue_id != -1:
                        if self.then_callback:
                            self.then_callback(
                                    self._then_queue_id
                                    , (self._unit_map['delay'], self._delay_buf)
                                    , self._unit_map['trigger']
                                    , self._unit_map['action']
                                    , self._unit_map['target']
                                    , self._message_buf
                                    , self._unit_map['stop']
                                    )
                        self._then_queue_id = -1
                    elif self.stop_callback:
                        self.stop_callback(
                                    self._unit_map['trigger']
                                    , self._unit_map['action']
                                    , self._unit_map['target']
                                    , self._message_buf
                                    , self._unit_map['stop']
                                    )
                    self._stop_succeed = False
                    self._reset_unit()

                self._message_buf = ''
                self._delay_buf = ''
                # self._reset()
            elif _token_type == "finish":
                self._FSM.found_finish_flag(self, _token)

                if self._finish_succeed :
                    if self._then_queue_id != -1:
                        if self.then_callback :
                            self.then_callback(
                                    self._then_queue_id
                                    , (self._unit_map['delay'], self._delay_buf)
                                    , self._unit_map['trigger']
                                    , self._unit_map['action']
                                    , self._unit_map['target']
                                    , self._message_buf
                                    , self._unit_map['finish']
                                    )
                        self._then_queue_id = -1
                    elif self.finish_callback and self._unit_map['action'] :
                        self.finish_callback(
                                (self._unit_map['delay'], self._delay_buf)
                                , self._unit_map['trigger']
                                , self._unit_map['action']
                                , self._unit_map['target']
                                , self._message_buf
                                , self._unit_map['finish']
                                )
                    self._finish_succeed = False
                    self._reset_unit()

                self._message_buf = ''
                self._delay_buf = ''
                # self._reset()
            elif _token_type == "then":
                self._FSM.found_then_flag(self, _token)

                if self._then_succeed:
                    if self.then_callback :
                        self.then_callback(
                                self._then_queue_id
                                , (self._unit_map['delay'], self._delay_buf)
                                , self._unit_map['trigger']
                                , self._unit_map['action']
                                , self._unit_map['target']
                                , self._message_buf
                                , self._unit_map['then']
                                )
                    self._then_succeed = False
                    self._reset_unit()
                self._message_buf = ''
                self._delay_buf = ''
            elif _token_type == "Else":
                self._FSM.found_else(self, _token)
                if self._FSM.current == 'delay_state':  # put it into buf here
                    self._delay_buf += _token

            if self._FSM.current == 'message_state':
                self._message_buf += _token

            if self._error_occoured:
                if self.DEBUG:
                    print "error occoured."
                if self._then_queue_id != -1:
                    if self.then_callback :
                            self.then_callback(
                                    self._then_queue_id
                                    , None
                                    , "Error" 
                                    , None 
                                    , None
                                    , None
                                    , None
                                    )
                    self._then_queue_id = -1
                self._FSM.reset()
                self._reset_unit()
            # print self._FSM.current

    def _reset_unit(self):
        self._unit_map = {
                'delay':"",
                'finish':"",
                'stop':"",
                'then':"",
                'trigger':"",
                'action':"",
                'target':"",
                }

    def reset(self):
        self._reset()

if __name__ == '__main__':
    def test_callback(trigger, action, target, message, finish):
        print "* finished >> action: %s, target: %s, message: %s" %(action, target, message)

    def stop_callback(trigger, action, target, message, finish):
        print "* stop >> action: %s, target: %s, message: %s" %(action, target, message)
    fsm = LE_Command_Parser(
            trigger = ["启动"],
            action = ["开", "关"],
            target = ["灯", "门"],
            stop = ["停止"],
            finish = ["结束"],
            then = ["然后", "接着"],
            DEBUG = True)
    fsm.finish_callback = test_callback
    fsm.stop_callback = stop_callback
    #TODO - "不要停&停止"
    parser_target = "启动台灯结束"
    fsm.put_into_parse_stream(parser_target)

