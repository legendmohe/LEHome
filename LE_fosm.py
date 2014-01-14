#!/usr/bin/env python
# encoding: utf-8

from fysom import Fysom

class LEFysom:

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

    def __reset(self):
        self.__unit_map = {
                'action':None,
                'target':None,
                'message':None
                }

    def finish_callback(self, action = None, target = None, message = None):
        pass

    def LE_fosm_parse(self, term):

        if self.DEBUG :
            print "parse: %s" %(term)

        if any(term in s for s in self.FLAG["trigger"]):
            self.__FSM.found_trigger(self, term)
        elif any(term in s for s in self.FLAG["action"]):
            self.__FSM.found_action(self, term)
        elif any(term in s for s in self.FLAG["target"]):
            self.__FSM.found_target(self, term)
        elif any(term in s for s in self.FLAG["stop"]):
            self.__FSM.found_stop_flag(self, term)
            self.__message_buf = ''
            self.__reset()
        elif any(term in s for s in self.FLAG["finish"]):
            self.__FSM.found_finish_flag(self, term)

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
        else:
            self.__FSM.found_else(self, term)

        if self.__FSM.current == 'message_state':
            self.__message_buf += term


if __name__ == '__main__':
    def test_callback(action, target, message):
        print ">> action: %s, target: %s, message: %s" %(action, target, message)

    fsm = LEFysom({
        'trigger':['a'],
        'action' :['b'],
        'target' :['c'],
        'stop' :['d'],
        'finish' :['e'],
        })
    fsm.DEBUG = True
    fsm.finish_callback = test_callback
    parser_target = "a,b,c,b,123123123,e,a,a,a,a,b,123123123,e,e,e,a,b,c,e,a,a"
    for term in parser_target.split(","):
        fsm.LE_fosm_parse(term)

