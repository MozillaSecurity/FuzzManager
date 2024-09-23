"""
Bugzilla Bug Provider Interface

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
"""

from django.forms.models import model_to_dict
from django.shortcuts import get_object_or_404
from django.utils import dateparse

from ..models import BugzillaTemplate, User
from .BugzillaREST import BugzillaREST
from .Provider import Provider


class BugzillaProvider(Provider):
    def __init__(self, pk, hostname):
        super().__init__(pk, hostname)

    def get_template_for_user(self, request, report_entry):
        if "template" in request.GET:
            obj = get_object_or_404(BugzillaTemplate, pk=request.GET["template"])
            template = model_to_dict(obj)
            template["pk"] = obj.pk
        else:
            user = User.objects.get_or_create(user=request.user)[0]

            default_template_id = user.default_template_id
            if not default_template_id:
                default_template_id = 1

            obj = BugzillaTemplate.objects.filter(pk=default_template_id).first()

            if not obj:
                template = {}
            else:
                template = model_to_dict(obj)
                template["pk"] = obj.pk

        return template

    def get_template_list(self):
        return BugzillaTemplate.objects.all()

    def get_bug_data(self, bug_id, username=None, password=None, api_key=None):
        bz = BugzillaREST(self.hostname, username, password, api_key)
        return bz.get_bug(bug_id)

    def get_bug_status(self, bug_ids, username=None, password=None, api_key=None):
        ret = {}
        bz = BugzillaREST(self.hostname, username, password, api_key)
        bugs = bz.get_bug_status(bug_ids)

        for bug_id in bugs:
            if bugs[bug_id]["is_open"]:
                ret[bug_id] = None
            elif bugs[bug_id]["dupe_of"]:
                ret[bug_id] = str(bugs[bug_id]["dupe_of"])
            else:
                ret[bug_id] = dateparse.parse_datetime(bugs[bug_id]["cf_last_resolved"])

        return ret
