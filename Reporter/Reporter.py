# encoding: utf-8
'''
Reporter -- Abstract base class for all reporters that use FuzzManager's config file

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''

# Ensure print() compatibility with Python 3
from __future__ import print_function

from abc import ABCMeta
import functools
import os
import platform
import time

import requests
import six


from FTB.ConfigurationFiles import ConfigurationFiles  # noqa


def remote_checks(wrapped):
    '''Decorator to perform error checks before using remote features'''
    @functools.wraps(wrapped)
    def decorator(self, *args, **kwargs):
        if not self.serverHost:
            raise RuntimeError("Must specify serverHost (configuration property: serverhost) to use remote features.")
        if not self.serverAuthToken:
            raise RuntimeError("Must specify serverAuthToken (configuration property: serverauthtoken) "
                               "to use remote features.")
        if not self.tool:
            raise RuntimeError("Must specify tool (configuration property: tool) to use remote features.")
        return wrapped(self, *args, **kwargs)
    return decorator


def signature_checks(wrapped):
    '''Decorator to perform error checks before using signature features'''
    @functools.wraps(wrapped)
    def decorator(self, *args, **kwargs):
        if not self.sigCacheDir:
            raise RuntimeError("Must specify sigCacheDir (configuration property: sigdir) to use signatures.")
        return wrapped(self, *args, **kwargs)
    return decorator


def requests_retry(wrapped):
    '''Wrapper around requests methods that retries up to 2 minutes if it's likely that the response codes indicate a
    temporary error'''
    @functools.wraps(wrapped)
    def wrapper(*args, **kwds):
        success = kwds.pop("expected")
        current_timeout = 2
        while True:
            response = wrapped(*args, **kwds)

            if response.status_code != success:
                # Allow for a total sleep time of up to 2 minutes if it's
                # likely that the response codes indicate a temporary error
                retry_codes = [500, 502, 503, 504]
                if response.status_code in retry_codes and current_timeout <= 64:
                    time.sleep(current_timeout)
                    current_timeout *= 2
                    continue

                raise Reporter.serverError(response)
            else:
                return response
        return wrapped(*args, **kwds)
    return wrapper


@six.add_metaclass(ABCMeta)
class Reporter():
    def __init__(self, sigCacheDir=None, serverHost=None, serverPort=None,
                 serverProtocol=None, serverAuthToken=None,
                 clientId=None, tool=None):
        '''
        Initialize the Reporter. This constructor will also attempt to read
        a configuration file to populate any missing properties that have not
        been passed to this constructor.

        @type sigCacheDir: string
        @param sigCacheDir: Directory to be used for caching signatures
        @type serverHost: string
        @param serverHost: Server host to contact for refreshing signatures
        @type serverPort: int
        @param serverPort: Server port to use when contacting server
        @type serverAuthToken: string
        @param serverAuthToken: Token for server authentication
        @type clientId: string
        @param clientId: Client ID stored in the server when submitting issues
        @type tool: string
        @param tool: Name of the tool that found this issue
        '''
        self.sigCacheDir = sigCacheDir
        self.serverHost = serverHost
        self.serverPort = serverPort
        self.serverProtocol = serverProtocol
        self.serverAuthToken = serverAuthToken
        self.clientId = clientId
        self.tool = tool
        self._session = requests.Session()

        # Now search for the global configuration file. If it exists, read its contents
        # and set all Collector settings that haven't been explicitely set by the user.
        globalConfigFile = os.path.join(os.path.expanduser("~"), ".fuzzmanagerconf")
        if os.path.exists(globalConfigFile):
            configInstance = ConfigurationFiles([globalConfigFile])
            globalConfig = configInstance.mainConfig

            if self.sigCacheDir is None and "sigdir" in globalConfig:
                self.sigCacheDir = globalConfig["sigdir"]

            if self.serverHost is None and "serverhost" in globalConfig:
                self.serverHost = globalConfig["serverhost"]

            if self.serverPort is None and "serverport" in globalConfig:
                self.serverPort = int(globalConfig["serverport"])

            if self.serverProtocol is None and "serverproto" in globalConfig:
                self.serverProtocol = globalConfig["serverproto"]

            if self.serverAuthToken is None:
                if "serverauthtoken" in globalConfig:
                    self.serverAuthToken = globalConfig["serverauthtoken"]
                elif "serverauthtokenfile" in globalConfig:
                    with open(globalConfig["serverauthtokenfile"]) as f:
                        self.serverAuthToken = f.read().rstrip()

            if self.clientId is None and "clientid" in globalConfig:
                self.clientId = globalConfig["clientid"]

            if self.tool is None and "tool" in globalConfig:
                self.tool = globalConfig["tool"]

        # Set some defaults that we can't set through default arguments, otherwise
        # they would overwrite configuration file settings
        if self.serverProtocol is None:
            self.serverProtocol = "https"

        # Try to be somewhat intelligent about the default port, depending on protocol
        if self.serverPort is None:
            if self.serverProtocol == "https":
                self.serverPort = 433
            else:
                self.serverPort = 80

        if self.serverHost is not None and self.clientId is None:
            self.clientId = platform.node()

    def get(self, *args, **kwds):
        """requests.get, with added support for FuzzManager authentication and retry on 5xx errors.

        @type expected: int
        @param expected: HTTP status code for successful response (default: requests.codes["ok"])
        """
        kwds.setdefault("expected", requests.codes["ok"])
        kwds.setdefault("headers", {}).update({"Authorization": "Token %s" % self.serverAuthToken})
        return requests_retry(self._session.get)(*args, **kwds)

    def post(self, *args, **kwds):
        """requests.post, with added support for FuzzManager authentication and retry on 5xx errors.

        @type expected: int
        @param expected: HTTP status code for successful response (default: requests.codes["created"])
        """
        kwds.setdefault("expected", requests.codes["created"])
        kwds.setdefault("headers", {}).update({"Authorization": "Token %s" % self.serverAuthToken})
        return requests_retry(self._session.post)(*args, **kwds)

    def patch(self, *args, **kwds):
        """requests.patch, with added support for FuzzManager authentication and retry on 5xx errors.

        @type expected: int
        @param expected: HTTP status code for successful response (default: requests.codes["created"])
        """
        kwds.setdefault("expected", requests.codes["ok"])
        kwds.setdefault("headers", {}).update({"Authorization": "Token %s" % self.serverAuthToken})
        return requests_retry(self._session.patch)(*args, **kwds)

    @staticmethod
    def serverError(response):
        return RuntimeError("Server unexpectedly responded with status code %s: %s" %
                            (response.status_code, response.text))
