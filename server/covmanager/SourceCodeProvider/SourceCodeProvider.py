'''
Source Code Provider Interface

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''

# Ensure print() compatibility with Python 3
from __future__ import print_function

from abc import ABCMeta, abstractmethod

class UnknownRevisionException(Exception):
    pass

class UnknownFilenameException(Exception):
    pass

class SourceCodeProvider():
    '''
    Abstract base class that defines what interfaces Source Code Providers must implement
    '''
    __metaclass__ = ABCMeta

    def __init__(self, location):
        self.location = location

    @abstractmethod
    def getSource(self, filename, revision):
        return

    @abstractmethod
    def update(self):
        return
