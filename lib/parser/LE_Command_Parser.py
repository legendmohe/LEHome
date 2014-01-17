#!/usr/bin/env python
# encoding: utf-8

from fysom import Fysom
from heapq import heappush, heapify

class LE_Command_Parser:

    FLAG = {
            "trigger" : [],
            "action" : [],
            "target" : [],
            "stop" : [],
            "finish" : [],
            }

    DEBUG = False

    __message_buf = ''
    __unit_map = {
            'action':None,
            'target':None,
            'message':None
            }

    __finish_succeed = False

    def onfound_trigger(self, e):
        if self.DEBUG:
            print 'event: %s, src: %s, dst: %s' % (e.event, e.src, e.dst)

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

        self.__finish_succeed = True

    def onfound_stop_flag(self, e):
        if self.DEBUG:
            print 'event: %s, src: %s, dst: %s' % (e.event, e.src, e.dst)


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

                    {'name': 'found_trigger', 'src': 'trigger_state',  'dst': 'trigger_state'},
                    {'name': 'found_action', 'src': 'trigger_state',  'dst': 'action_state'},
                    {'name': 'found_target', 'src': 'trigger_state',  'dst': 'initial_state'},
                    {'name': 'found_else', 'src': 'trigger_state',  'dst': 'initial_state'},
                    {'name': 'found_finish_flag', 'src': 'trigger_state',  'dst': 'initial_state'},

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
                    {'name': 'found_stop_flag', 'src': ['trigger_state', 'action_state', 'target_state', 'message_state'], 'dst': 'initial_state'},
                    {'name': 'found_finish_flag', 'src': ['action_state', 'target_state', 'message_state'], 'dst': 'initial_state'},
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

        self.__token_buf = []
        self.__match_stack = []
    
    def __reset(self):
        self.__unit_map = {
                'action':None,
                'target':None,
                'message':None
                }

    def __parse_token(self, item):
        self.__token_buf.append(item)
        _temp_str = "".join(self.__token_buf)
        _no_match = True
        _index = 1
        for token_tuple in self.FLAG:
            _match = False
            _token_type = (_index, token_tuple[0])
            for match_str in token_tuple[1]:
                if match_str.startswith(_temp_str):
                    _match = True
                    _no_match = False
                    if _token_type not in self.__match_stack:
                        heappush(self.__match_stack, _token_type) # use heap
                    if len(match_str) == len(_temp_str):
                        if self.__match_stack[0] == _token_type:
                            del self.__match_stack[:]
                            del self.__token_buf[:]
                            return _temp_str, _token_type[1]
                    break
                elif _temp_str.startswith(match_str):
                    _match = True
                    _no_match = False
                    if _token_type not in self.__match_stack:
                        heappush(self.__match_stack, _token_type)
                    if self.__match_stack[0] == _token_type:
                        del self.__match_stack[:]
                        del self.__token_buf[0:len(match_str)]
                        return _temp_str, _token_type[1]
                    break

            if not _match and _token_type in self.__match_stack:
                self.__match_stack.remove(_token_type)
                heapify(self.__match_stack)

            _index += 1

        if _no_match:
            return self.__token_buf.pop(0), "Else"

        return None, None
                

    # callback func
    def finish_callback(self, action = None, target = None, message = None):
        pass

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
                self.__message_buf = ''
                self.__reset()
            elif _token_type == "finish":
                self.__FSM.found_finish_flag(self, _token)

                if self.__finish_succeed :
                    self.__unit_map['message'] = self.__message_buf
                    self.finish_callback(
                            self.__unit_map['action']
                            , self.__unit_map['target']
                            , self.__unit_map['message']
                            )
                    self.__finish_succeed = False

                self.__message_buf = ''
                self.__reset()
            elif _token_type == "Else":
                self.__FSM.found_else(self, _token)

            if self.__FSM.current == 'message_state':
                self.__message_buf += _token


if __name__ == '__main__':
    def test_callback(action, target, message):
        print ">> action: %s, target: %s, message: %s" %(action, target, message)

    fsm = LE_Command_Parser([
        ('trigger' ,['aaba']),
        ('stop' , ['aab']),
        ('finish' , ['ee']),
        ('action' , ['ba']),
        ('target' , ['cba']),
        ])
    fsm.DEBUG = True
    fsm.finish_callback = test_callback
    parser_target = "aabeaababacba4234234234324ee"
    for term in list(parser_target):
        fsm.put_into_parse_stream(term)

