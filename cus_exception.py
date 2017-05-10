#-*- coding: utf-8 -*-

import logging
import datetime


class CusException(Exception):
    def __init__(self, name, error_msg):
        super(CusException, self).__init__(name, error_msg)
        self.name = name

        if type(error_msg) == CusException:
            self.error_msg = error_msg.error_msg
        else:
            self.error_msg = error_msg

        self.error_time = str(datetime.datetime.now())
