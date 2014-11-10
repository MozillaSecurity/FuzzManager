'''
Bug Provider Interface

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

class Provider():
    '''
    Abstract base class that defines what interfaces Bug Providers must implement
    '''
    __metaclass__ = ABCMeta
    
    def __init__(self, hostname):
        self.hostname = hostname
    
    @abstractmethod
    def renderContextCreate(self, request, crashEntry):
        return
    
    @abstractmethod
    def handlePOSTCreate(self, request):
        return
    
    @abstractmethod
    def getBugData(self, bugId, username, password):
        return
    
