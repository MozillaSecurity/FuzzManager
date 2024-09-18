"""
Bugzilla REST Abstraction Layer

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
"""
import requests


class BugzillaREST:
    def __init__(self, hostname, username=None, password=None, api_key=None):
        self.hostname = hostname
        self.base_url = f"https://{self.hostname}/rest"
        self.username = username
        self.password = password
        self.api_key = api_key
        self.auth_token = None
        self.request_headers = {}

        # If we have no username, no API key but a password, use the password
        # as the API key, as the UI has no extra field for the API key.
        if username is None and api_key is None and password is not None:
            self.api_key = password
            self.password = None

        if self.api_key is not None:
            # Transmit the API key via request header instead of embedding
            # it in the URI for additional security.
            self.request_headers["X-BUGZILLA-API-KEY"] = self.api_key

    def login(self, login_required=True, force_login=False):
        if (self.username is None or self.password is None) and self.api_key is None:
            if login_required:
                raise RuntimeError("Need username/password or API key to login.")
            else:
                return False

        # If we have an API key, we don't need to perform any login
        if self.api_key is not None:
            return False

        if force_login:
            self.auth_token = None

        # We might still have a valid authentication token that we can use.
        if self.auth_token is not None:
            return True

        login_url = (
            f"{self.base_url}/login?login={self.username}&password={self.password}"
        )
        response = requests.get(login_url)
        json = response.json()

        if "token" not in json:
            raise RuntimeError(f"Login failed: {response.text}")

        self.auth_token = json["token"]
        return True

    def get_bug(self, bug_id):
        bugs = self.get_bugs([bug_id])

        if not bugs:
            return None

        return bugs[int(bug_id)]

    def get_bug_status(self, bug_ids):
        return self.get_bugs(
            bug_ids,
            include_fields=[
                "id",
                "is_open",
                "resolution",
                "dupe_of",
                "cf_last_resolved",
            ],
        )

    def get_bugs(self, bug_ids, include_fields=None, exclude_fields=None):
        if not isinstance(bug_ids, list):
            bug_ids = [bug_ids]

        bug_url = f"{self.base_url}/bug?id={','.join(bug_ids)}"

        extra_params = []

        # Ensure we are logged in if we have any login data.
        # However, we might not need any credentials for reading bugs.
        if self.login(login_required=False):
            extra_params.append(f"&token={self.auth_token}")

        if include_fields:
            extra_params.append(f"&include_fields={','.join(include_fields)}")

        if exclude_fields:
            extra_params.append(f"&exclude_fields={','.join(exclude_fields)}")

        response = requests.get(
            bug_url + "".join(extra_params), headers=self.request_headers
        )
        json = response.json()

        if "bugs" not in json:
            raise RuntimeError(f"Query failed: {response.text}")

        ret = {}
        for bug in json["bugs"]:
            ret[bug["id"]] = bug

        return ret
