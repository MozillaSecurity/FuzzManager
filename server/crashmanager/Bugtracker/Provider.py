"""
Bug Provider Interface

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
"""

from __future__ import annotations

from abc import ABCMeta, abstractmethod

from django.db.models.query import QuerySet

from ..models import BugzillaTemplate


class Provider(metaclass=ABCMeta):
    """
    Abstract base
    class that defines what interfaces Bug Providers must implement
    """

    def __init__(self, pk: int, hostname: str) -> None:
        self.pk = pk
        self.hostname = hostname

    @abstractmethod
    def getTemplateList(self) -> QuerySet[BugzillaTemplate]:
        return

    @abstractmethod
    def getBugData(
        self, bugId: str, username: str | None = None, password: str | None = None
    ) -> str | None:
        return

    @abstractmethod
    def getBugStatus(
        self,
        bugIds: list[str],
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        return
