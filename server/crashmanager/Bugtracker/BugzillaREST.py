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
