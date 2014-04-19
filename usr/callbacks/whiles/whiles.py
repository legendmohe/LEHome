#!/usr/bin/env python
# encoding: utf-8


from lib.model import Callback


class while_callback(Callback.Callback):
    def callback(
            self,
            whiles=None,
            msg=None,
            action=None,
            target=None,
            pre_value=None
            ):
        return True, "while"
