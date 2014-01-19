#!/usr/bin/env python
# encoding: utf-8

from fysom import Fysom
from heapq import heappush, heapify
import time

class LE_Command_Parser:

    FLAG = {
            "trigger" : [],
            "action" : [],
            "target" : [],
            "stop" : [],
            "finish" : [],
            "then" :[],
            }

    DEBUG = False

    __message_buf = ''
    __unit_map = {
            'finish':"",
            'stop':"",
            'then' :"",
            'trigger':"",
            'action':"",
            'target':"",
            'message':""
            }

    __finish_succeed = False
    __stop_succeed = False
    __then_succeed = False
    __then_queue_id = -1

    def onfound_trigger(self, e):
        if self.DEBUG:
            print 'event: %s, src: %s, dst: %s' % (e.event, e.src, e.dst)
        self.__unit_map['trigger'] = e.args[1]

    def onfound_target(self, e):
        if self.DEBUG:
            print 'event: %s, src: %s, dst: %s' % (e.event, e.src, e.dst)
        self.__unit_map['target'] = e.args[1]

    def onfound_action(self, e):
        if self.DEBUG:
            print 'event: %s, src: %s, dst: %s' % (e.event, e.src, e.dst)
        self.__unit_map['action'] = e.args[1]

    def onfound_else(self, e):
        if self.DEBUG:
            print 'event: %s, src: %s, dst: %s' % (e.event, e.src, e.dst)

    def onfound_finish_flag(self, e):
        if self.DEBUG:
            print 'finish ! = event: %s, src: %s, dst: %s' % (e.event, e.src, e.dst)

        self.__unit_map['finish'] = e.args[1]
        self.__finish_succeed = True

    def onfound_stop_flag(self, e):
        if self.DEBUG:
            print 'event: %s, src: %s, dst: %s' % (e.event, e.src, e.dst)

        self.__unit_map['stop'] = e.args[1]
        self.__stop_succeed = True

    def onfound_then_flag(self, e):
        if self.DEBUG:
            print 'event: %s, src: %s, dst: %s' % (e.event, e.src, e.dst)

        self.__unit_map['then'] = e.args[1]
        self.__then_succeed = True
        if self.__then_queue_id == -1:
            self.__then_queue_id = int(time.time())

    __FSM = Fysom({
        'initial': 'initial_state',
        #'final': 'initial_state',
        'events': [
                    {'name': 'found_trigger', 'src': 'initial_state',  'dst': 'trigger_state'},
                    {'name': 'found_action', 'src': 'initial_state',  'dst': 'initial_state'},
                    {'name': 'found_target', 'src': 'initial_state',  'dst': 'initial_state'},
                    {'name': 'found_else', 'src': 'initial_state',  'dst': 'initial_state'},
                    {'name': 'found_stop_flag', 'src': 'initial_state',  'dst': 'initial_state'},
                    {'name': 'found_finish_flag', 'src': 'initial_state',  'dst': 'initial_state'},
                    {'name': 'found_then_flag', 'src': 'initial_state',  'dst': 'initial_state'},

                    {'name': 'found_trigger', 'src': 'trigger_state',  'dst': 'trigger_state'},
                    {'name': 'found_action', 'src': 'trigger_state',  'dst': 'action_state'},
                    {'name': 'found_target', 'src': 'trigger_state',  'dst': 'initial_state'},
                    {'name': 'found_else', 'src': 'trigger_state',  'dst': 'initial_state'},
                    {'name': 'found_finish_flag', 'src': 'trigger_state',  'dst': 'initial_state'},
                    {'name': 'found_then_flag', 'src': 'trigger_state',  'dst': 'initial_state'},

                    {'name': 'found_trigger', 'src': 'action_state',  'dst': 'message_state'},
                    {'name': 'found_action', 'src': 'action_state',  'dst': 'initial_state'},
                    {'name': 'found_target', 'src': 'action_state',  'dst': 'target_state'},
                    {'name': 'found_else', 'src': 'action_state',  'dst': 'message_state'},

                    {'name': 'found_trigger', 'src': 'target_state',  'dst': 'message_state'},
                    {'name': 'found_action', 'src': 'target_state',  'dst': 'message_state'},
                    {'name': 'found_target', 'src': 'target_state',  'dst': 'message_state'},
                    {'name': 'found_else', 'src': 'target_state',  'dst': 'message_state'},

                    {'name': 'found_trigger', 'src': 'message_state',  'dst': 'message_state'},
                    {'name': 'found_action', 'src': 'message_state',  'dst': 'message_state'},
                    {'name': 'found_target', 'src': 'message_state',  'dst': 'message_state'},
                    {'name': 'found_else', 'src': 'message_state',  'dst': 'message_state'},

                    {'name': 'reset', 'src': '*',  'dst': 'initial_state'},
                    {'name': 'found_stop_flag',
                        'src': ['trigger_state', 'action_state', 'target_state', 'message_state'], 
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

    def __init__(self, FLAG = None):
        if FLAG :
            self.FLAG = FLAG

        self.__FSM.onfound_trigger = self.onfound_trigger
        self.__FSM.onfound_else = self.onfound_else
        self.__FSM.onfound_action = self.onfound_action
        self.__FSM.onfound_target = self.onfound_target
        self.__FSM.onfound_finish_flag = self.onfound_finish_flag
        self.__FSM.onfound_stop_flag = self.onfound_stop_flag
        self.__FSM.onfound_then_flag = self.onfound_then_flag

        self.__token_buf = []
        self.__match_stack = []

        self.finish_callback = None
        self.stop_callback = None
        self.then_callback = None
    
    def __reset(self):
        self.__unit_map = {
                'finish':"",
                'stop':"",
                'then':"",
                'trigger':"",
                'action':"",
                'target':"",
                'message':""
                }
        self.__FSM.current = "initial_state"
        del self.__token_buf[:]
        del self.__match_stack[:]

    def __parse_token(self, word):
        self.__token_buf.append(word)
        _temp_str = "".join(self.__token_buf)
        _no_match = True
        _index = 1
        for token_tuple in self.FLAG: 
            _found_match_in_token_flag_array = False # a flag that indicate if all mis-match or not
            _token_type = (_index, token_tuple[0]) #item in heap is tuple (index, item)

            for match_str in token_tuple[1]:
                if match_str.startswith(_temp_str):
                    _found_match_in_token_flag_array = True #found match
                    _no_match = False #for no match in each match token
                    if _token_type not in self.__match_stack:
                        heappush(self.__match_stack, _token_type) # use heap
                        
                    if len(match_str) == len(_temp_str):
                        # if current match type is on top of heap, that means it has the
                        # highest priority.now it totally match the buf, so we get the 
                        # token type
                        if self.__match_stack[0] == _token_type: 
                            del self.__match_stack[:]
                            del self.__token_buf[:]
                            return _temp_str, _token_type[1] #that we found the final type

                    # we found the current buf's token type, so we clean the scene
                    break

                # in case that token has shorter token length then the buf
                elif _temp_str.startswith(match_str):
                    _found_match_in_token_flag_array = True
                    _no_match = False
                    if _token_type not in self.__match_stack:
                        heappush(self.__match_stack, _token_type)

                    # in case that lower token has short lengh, and it match
                    if self.__match_stack[0] == _token_type:
                        del self.__match_stack[:]
                        del self.__token_buf[0:len(match_str)] #r
                        return _temp_str, _token_type[1]
                    break

            #buf will never match the current token type, so we pop it
            if not _found_match_in_token_flag_array and _token_type in self.__match_stack:
                self.__match_stack.remove(_token_type)
                heapify(self.__match_stack)

            _index += 1

        if _no_match:
            return self.__token_buf.pop(0), "Else"

        return None, None
                
    def put_into_parse_stream(self, stream_term):

        if self.DEBUG :
            print "parse: %s" %(stream_term)

        for item in list(stream_term):
            _token, _token_type = self.__parse_token(item)
            if _token == None:
                #print "continue"
                continue
            if _token_type == "trigger":
                self.__FSM.found_trigger(self, _token)
            elif _token_type == "action":
                self.__FSM.found_action(self, _token)
            elif _token_type == "target":
                self.__FSM.found_target(self, _token)
            elif _token_type == "stop":
                self.__FSM.found_stop_flag(self, _token)
                
                if self.__stop_succeed:
                    if self.stop_callback:
                        self.stop_callback(
                                    self.__unit_map['trigger']
                                    , self.__unit_map['action']
                                    , self.__unit_map['target']
                                    , self.__unit_map['message']
                                    , self.__unit_map['stop']
                                    )
                    self.__stop_succeed = False
                    self.__unit_map = {
                            'finish':"",
                            'stop':"",
                            'then':"",
                            'trigger':"",
                            'action':"",
                            'target':"",
                            'message':""
                            }

                self.__message_buf = ''
                # self.__reset()
            elif _token_type == "finish":
                self.__FSM.found_finish_flag(self, _token)

                if self.__finish_succeed :
                    self.__unit_map['message'] = self.__message_buf
                    if self.__then_queue_id != -1:
                        if self.then_callback :
                            self.then_callback(
                                    self.__then_queue_id
                                    , self.__unit_map['trigger']
                                    , self.__unit_map['action']
                                    , self.__unit_map['target']
                                    , self.__unit_map['message']
                                    , self.__unit_map['finish']
                                    )
                        self.__then_queue_id = -1
                    elif self.finish_callback and self.__unit_map['action'] :
                        self.finish_callback(
                                self.__unit_map['trigger']
                                , self.__unit_map['action']
                                , self.__unit_map['target']
                                , self.__unit_map['message']
                                , self.__unit_map['finish']
                                )
                    self.__finish_succeed = False
                    self.__unit_map = {
                            'finish':"",
                            'stop':"",
                            'then':"",
                            'trigger':"",
                            'action':"",
                            'target':"",
                            'message':""
                            }

                self.__message_buf = ''
                # self.__reset()
            elif _token_type == "then":
                self.__FSM.found_then_flag(self, _token)

                if self.__then_succeed:
                    self.__unit_map['message'] = self.__message_buf
                    if self.then_callback :
                        self.then_callback(
                                self.__then_queue_id
                                , self.__unit_map['trigger']
                                , self.__unit_map['action']
                                , self.__unit_map['target']
                                , self.__unit_map['message']
                                , None
                                )
                    self.__then_succeed = False
                    self.__unit_map = {
                            'finish':"",
                            'stop':"",
                            'then':"",
                            'trigger':"",
                            'action':"",
                            'target':"",
                            'message':""
                            }
                self.__message_buf = ''
            elif _token_type == "Else":
                self.__FSM.found_else(self, _token)

            if self.__FSM.current == 'message_state':
                self.__message_buf += _token

    def reset(self):
        self.__reset()

if __name__ == '__main__':
    def test_callback(trigger, action, target, message, finish):
        print "* finished >> action: %s, target: %s, message: %s" %(action, target, message)

    def stop_callback(trigger, action, target, message, finish):
        print "* stop >> action: %s, target: %s, message: %s" %(action, target, message)
    fsm = LE_Command_Parser([
        ('trigger' ,['启动']),
        ('stop' , ['停止']),
        ('finish' , ['结束']),
        ('action' , ['开']),
        ('target' , ['灯']),
        ])
    fsm.DEBUG = False
    fsm.finish_callback = test_callback
    fsm.stop_callback = stop_callback
    #TODO - "不要停&停止"
    parser_target = "你好启动开灯结束你好今天天气启动开灯不开停止启动启动结束启动开灯123结束"
    for term in list(parser_target):
        fsm.put_into_parse_stream(term)

