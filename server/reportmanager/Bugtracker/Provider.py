"""
Bug Provider Interface

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
"""
from abc import ABCMeta, abstractmethod


class Provider(metaclass=ABCMeta):
    """
    Abstract base
    class that defines what interfaces Bug Providers must implement
    """

    def __init__(self, pk, hostname):
        self.pk = pk
        self.hostname = hostname

    @abstractmethod
    def get_template_list(self):
        return

    @abstractmethod
    def get_bug_data(self, bug_id, username=None, password=None):
        return

    @abstractmethod
    def get_bug_status(self, bug_ids, username=None, password=None):
        return
