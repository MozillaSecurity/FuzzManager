# encoding: utf-8
'''
StreamCollector -- Runs as a thread and reads a single output stream of a process.

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''

# Ensure print() compatibility with Python 3
from __future__ import print_function

import threading

from six.moves import queue


class StreamCollector(threading.Thread):
    def __init__(self, fd, responseQueue, logResponses=False, maxBacklog=None):
        assert callable(fd.readline)
        assert isinstance(responseQueue, queue.Queue)

        threading.Thread.__init__(self)

        self.fd = fd
        self.queue = responseQueue
        self.output = []
        self.responsePrefixes = []
        self.logResponses = logResponses
        self.maxBacklog = maxBacklog

    def run(self):
        while True:
            line = self.fd.readline(4096)

            if not line:
                break

            isResponse = False
            for prefix in self.responsePrefixes:
                line = line.rstrip('\n')
                if line.startswith(prefix):
                    self.queue.put(line.replace(prefix, ''))
                    isResponse = True
                    break

            if not isResponse or self.logResponses:
                self.output.append(line)

                # With maxBacklog specified, emulate a FIFO with the given length
                if self.maxBacklog is not None and len(self.output) > self.maxBacklog:
                    self.output.pop(0)

        self.fd.close()

    def addResponsePrefix(self, prefix):
        self.responsePrefixes.append(prefix)
