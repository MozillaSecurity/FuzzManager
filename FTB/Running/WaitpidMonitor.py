# encoding: utf-8
'''
WaitpidMonitor -- Thread that runs (blocking) waitpid on a process.
                  Can be used to simulate waitpid with timeout.

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''

# Ensure print() compatibility with Python 3
from __future__ import print_function

import os
import threading


class WaitpidMonitor(threading.Thread):
    def __init__(self, pid, options):
        threading.Thread.__init__(self)

        self.pid = pid
        self.options = options

        self.childPid = None
        self.childExit = None

    def run(self):
        while not self.childPid:
            (self.childPid, self.childExit) = os.waitpid(self.pid, self.options)
