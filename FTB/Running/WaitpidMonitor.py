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

from __future__ import annotations

import os
import threading


class WaitpidMonitor(threading.Thread):
    def __init__(self, pid: int, options: int) -> None:
        threading.Thread.__init__(self)

        self.pid: int = pid
        self.options: int = options

        self.childPid: int | None = None
        self.childExit: int | None = None

    def run(self) -> None:
        while not self.childPid:
            (self.childPid, self.childExit) = os.waitpid(self.pid, self.options)
