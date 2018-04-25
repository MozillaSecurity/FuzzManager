'''
Bugzilla REST Abstraction Layer

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''

# Ensure print() compatibility with Python 3
from __future__ import print_function

import base64
import requests


class BugzillaREST():
    def __init__(self, hostname, username=None, password=None, api_key=None):
        self.hostname = hostname
        self.baseUrl = 'https://%s/rest' % self.hostname
        self.username = username
        self.password = password
        self.api_key = api_key
        self.authToken = None

        # If we have no username, no API key but a password, switch API key and password
        if username is None and api_key is None and password is not None:
            self.api_key = password
            self.password = None

        # The field to submit authentication information in depends on which
        # method we use (username/password means we need to use token, with
        # API key we can use the api_key field directly).
        self.authField = 'token'
        if self.api_key is not None:
            self.authField = 'api_key'

    def login(self, forceLogin=False):
        if (self.username is None or self.password is None) and self.api_key is None:
            if forceLogin:
                raise RuntimeError("Need username/password or API key to login.")
            else:
                return False

        if forceLogin:
            self.authToken = None

        if self.api_key is not None:
            self.authToken = self.api_key

        # We either use an API key which doesn't require any prior login
        # or we still have a valid authentication token that we can use.
        if self.authToken is not None:
            return True

        loginUrl = "%s/login?login=%s&password=%s" % (self.baseUrl, self.username, self.password)
        response = requests.get(loginUrl)
        json = response.json()

        if 'token' not in json:
            raise RuntimeError('Login failed: %s', response.text)

        self.authToken = json["token"]
        return True

    def getBug(self, bugId):
        bugs = self.getBugs([bugId])

        if not bugs:
            return None

        return bugs[int(bugId)]

    def getBugStatus(self, bugIds):
        return self.getBugs(bugIds, include_fields=["id", "is_open", "resolution", "dupe_of", "cf_last_resolved"])

    def getBugs(self, bugIds, include_fields=None, exclude_fields=None):
        if not isinstance(bugIds, list):
            bugIds = [bugIds]

        bugUrl = "%s/bug?id=%s" % (self.baseUrl, ",".join(bugIds))

        extraParams = []

        if self.login():
            extraParams.append("&%s=%s" % (self.authField, self.authToken))

        if include_fields:
            extraParams.append("&include_fields=%s" % ",".join(include_fields))

        if exclude_fields:
            extraParams.append("&exclude_fields=%s" % ",".join(exclude_fields))

        response = requests.get(bugUrl + "".join(extraParams))
        json = response.json()

        if "bugs" not in json:
            return None

        ret = {}
        for bug in json["bugs"]:
            ret[bug["id"]] = bug

        return ret

    def createBug(self, product, component, summary, version, description=None, op_sys=None,
                  platform=None, priority=None, severity=None, alias=None,
                  cc=None, assigned_to=None, comment_is_private=None, is_markdown=None,
                  groups=None, qa_contact=None, status=None, resolution=None,
                  target_milestone=None, flags=None, whiteboard=None, keywords=None, attrs=None):

        # Compose our bug attribute using all given arguments with special
        # handling of the self and attrs arguments
        loc = locals()
        bug = {}
        for k in loc:
            if k == "attrs" and loc[k] is not None:
                for ak in loc[k]:
                    bug[ak] = loc[k][ak]
            elif loc[k] is not None and loc[k] != '' and k != "self":
                bug[k] = loc[k]

        # Ensure we're logged in
        self.login()

        createUrl = "%s/bug?%s=%s" % (self.baseUrl, self.authField, self.authToken)
        response = requests.post(createUrl, bug)
        return response.json()

    def createComment(self, id, comment, is_private=False):
        if is_private:
            is_private = 1
        else:
            is_private = 0
        cobj = {}
        cobj["comment"] = comment
        cobj["is_private"] = is_private

        # Ensure we're logged in
        self.login()

        createUrl = "%s/bug/%s/comment?%s=%s" % (self.baseUrl, id, self.authField, self.authToken)
        response = requests.post(createUrl, cobj).json()

        if "id" not in response:
            return response

        commentId = str(response["id"])

        commentUrl = "%s/bug/comment/%s?%s=%s" % (self.baseUrl, commentId, self.authField, self.authToken)
        response = requests.get(commentUrl).json()

        if "comments" not in response:
            return response

        if commentId not in response["comments"]:
            return response

        return response["comments"][commentId]

    def addAttachment(self, ids, data, file_name, summary, comment=None, is_private=None, is_binary=False):
        # Compose our request using all given arguments with special
        # handling of the self and is_binary arguments
        loc = locals()
        attachment = {}
        for k in loc:
            if loc[k] is not None and loc[k] != '' and k != "self" and k != "is_binary":
                attachment[k] = loc[k]

        # Set proper content-type
        if is_binary:
            attachment["content_type"] = "application/octet-stream"
        else:
            attachment["content_type"] = "text/plain"

        # Attachment data must always be base64 encoded
        attachment["data"] = base64.b64encode(attachment["data"])

        # Ensure we're logged in
        self.login()

        attachUrl = "%s/bug/%s/attachment?%s=%s" % (self.baseUrl, ids, self.authField, self.authToken)
        response = requests.post(attachUrl, attachment)
        return response.json()
