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

import six


@six.add_metaclass(ABCMeta)
class Provider():
    '''
    Abstract base
    class that defines what interfaces Bug Providers must implement
    '''
    def __init__(self, pk, hostname):
        self.pk = pk
        self.hostname = hostname

    @abstractmethod
    def renderContextCreate(self, request, crashEntry):
        return

    @abstractmethod
    def renderContextComment(self, request, crashEntry):
        return

    @abstractmethod
    def handlePOSTCreate(self, request, crashEntry):
        return

    @abstractmethod
    def handlePOSTComment(self, request, crashEntry):
        return

    @abstractmethod
    def renderContextCreateTemplate(self, request):
        return

    @abstractmethod
    def renderContextViewTemplate(self, request, templateId, mode):
        return

    @abstractmethod
    def handlePOSTCreateEditTemplate(self, request):
        return

    @abstractmethod
    def getTemplateList(self):
        return

    @abstractmethod
    def getBugData(self, bugId, username=None, password=None):
        return

    @abstractmethod
    def getBugStatus(self, bugIds, username=None, password=None):
        return
