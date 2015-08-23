#!/usr/bin/env python
#
# io test code for pcDuino ( http://www.pcduino.com )
#
__all__ = ['HIGH', 'LOW', 'INPUT', 'OUTPUT','digitalWrite', 'digitalRead', "pinMode"]

_GPIO_PINS = ('gpio0','gpio1','gpio2','gpio3','gpio4','gpio5','gpio6','gpio7',
                'gpio8', 'gpio9', 'gpio10', 'gpio11', 'gpio12', 'gpio13',
                'gpio14', 'gpio15', 'gpio16', 'gpio17', 'gpio18', 'gpio19')

_PIN_FD_PATH = '/sys/devices/virtual/misc/gpio/pin/%s'
_MODE_FD_PATH = '/sys/devices/virtual/misc/gpio/mode/%s'
HIGH = 1
LOW = 0
INPUT = 0
OUTPUT = 1

class InvalidChannelException(Exception):
    """The channel sent is invalid on pcDuino board """
    pass

def _GetValidId(channel):
    if channel in _GPIO_PINS:
        return channel
    else:
        raise InvalidChannelException

def digitalWrite(channel, value):
    """Write to a GPIO channel"""
    id = _GetValidId(channel)
    with open(_PIN_FD_PATH % id, 'w') as f:
        f.write('1' if value == HIGH else '0')

def digitalRead(channel):
    """Read from a GPIO channel"""
    id = _GetValidId(channel)
    with open(_PIN_FD_PATH % id, 'r') as f:
        return f.read(1) == '1'

def pinMode(channel, mode):
    """ Set Mode of a GPIO channel """
    id = _GetValidId(channel)
    with open(_MODE_FD_PATH % id, 'w') as f:
        f.write('0' if mode == INPUT else '1')
