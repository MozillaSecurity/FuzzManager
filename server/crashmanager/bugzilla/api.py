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
        self.request_headers = {}

        # If we have no username, no API key but a password, use the password
        # as the API key, as the UI has no extra field for the API key.
        if username is None and api_key is None and password is not None:
            self.api_key = password
            self.password = None

        if self.api_key is not None:
            # Transmit the API key via request header instead of embedding
            # it in the URI for additional security.
            self.request_headers['X-BUGZILLA-API-KEY'] = self.api_key

    def login(self, loginRequired=True, forceLogin=False):
        if (self.username is None or self.password is None) and self.api_key is None:
            if loginRequired:
                raise RuntimeError("Need username/password or API key to login.")
            else:
                return False

        # If we have an API key, we don't need to perform any login
        if self.api_key is not None:
            return False

        if forceLogin:
            self.authToken = None

        # We might still have a valid authentication token that we can use.
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

        # Ensure we are logged in if we have any login data.
        # However, we might not need any credentials for reading bugs.
        if self.login(loginRequired=False):
            extraParams.append("&token=%s" % self.authToken)

        if include_fields:
            extraParams.append("&include_fields=%s" % ",".join(include_fields))

        if exclude_fields:
            extraParams.append("&exclude_fields=%s" % ",".join(exclude_fields))

        response = requests.get(bugUrl + "".join(extraParams), headers=self.request_headers)
        json = response.json()

        if "bugs" not in json:
            return None

        ret = {}
        for bug in json["bugs"]:
            ret[bug["id"]] = bug

        return ret

    def createBug(self, product, component, summary, version, type='defect', description=None,
                  op_sys=None, platform=None, priority=None, severity=None, alias=None,
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

        createUrl = "%s/bug" % self.baseUrl

        # Ensure we're logged in, if required
        if self.login():
            createUrl = "%s?token=%s" % (createUrl, self.authToken)

        response = requests.post(createUrl, bug, headers=self.request_headers)
        return response.json()

    def createComment(self, id, comment, is_private=False):
        if is_private:
            is_private = 1
        else:
            is_private = 0
        cobj = {}
        cobj["comment"] = comment
        cobj["is_private"] = is_private

        createUrl = "%s/bug/%s/comment" % (self.baseUrl, id)

        # Ensure we're logged in, if required
        if self.login():
            createUrl = "%s?token=%s" % (createUrl, self.authToken)
        response = requests.post(createUrl, cobj, headers=self.request_headers).json()

        if "id" not in response:
            return response

        commentId = str(response["id"])
        commentUrl = "%s/bug/comment/%s" % (self.baseUrl, commentId)

        if self.login():
            commentUrl = "%s?token=%s" % (commentUrl, self.authToken)
        response = requests.get(commentUrl, headers=self.request_headers).json()

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

        attachUrl = "%s/bug/%s/attachment" % (self.baseUrl, ids)

        # Ensure we're logged in, if required
        if self.login():
            attachUrl = "%s?token=%s" % (attachUrl, self.authToken)
        response = requests.post(attachUrl, attachment, headers=self.request_headers)
        return response.json()
