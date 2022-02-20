'''
Bugzilla Bug Provider Interface

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''

from __future__ import annotations

from django.db.models.query import QuerySet
from django.forms.models import model_to_dict
from django.shortcuts import get_object_or_404
from django.utils import dateparse

from .BugzillaREST import BugzillaREST
from .Provider import Provider
from ..models import BugzillaTemplate, CrashEntry, User


class BugzillaProvider(Provider):
    def __init__(self, pk: int, hostname: str) -> None:
        super(BugzillaProvider, self).__init__(pk, hostname)

    def getTemplateForUser(self, request, crashEntry: CrashEntry):
        if 'template' in request.GET:
            obj = get_object_or_404(BugzillaTemplate, pk=request.GET['template'])
            template = model_to_dict(obj)
            template["pk"] = obj.pk
        else:
            user = User.get_or_create_restricted(request.user)[0]

            obj = BugzillaTemplate.objects.filter(name__contains=crashEntry.tool.name)
            if not obj:
                defaultTemplateId = user.defaultTemplateId
                if not defaultTemplateId:
                    defaultTemplateId = 1

                obj = BugzillaTemplate.objects.filter(pk=defaultTemplateId)

            if not obj:
                template = {}
            else:
                template = model_to_dict(obj[0])
                template["pk"] = obj[0].pk

        return template

    def getTemplateList(self) -> QuerySet[BugzillaTemplate]:
        return BugzillaTemplate.objects.all()

    def getBugData(self, bugId: str, username: str | None = None, password: str | None = None, api_key: str | None = None) -> str | None:
        bz = BugzillaREST(self.hostname, username, password, api_key)
        return bz.getBug(bugId)

    def getBugStatus(self, bugIds: list[str], username: str | None = None, password: str | None = None, api_key: str | None = None):
        ret = {}
        bz = BugzillaREST(self.hostname, username, password, api_key)
        bugs = bz.getBugStatus(bugIds)

        assert bugs is not None
        for bugId in bugs:
            if bugs[bugId]["is_open"]:
                ret[bugId] = None
            elif bugs[bugId]["dupe_of"]:
                ret[bugId] = str(bugs[bugId]["dupe_of"])
            else:
                ret[bugId] = dateparse.parse_datetime(bugs[bugId]["cf_last_resolved"])

        return ret
