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

from __future__ import annotations

from abc import ABC
from collections.abc import Callable
import functools
import logging
import os
import platform
import time
from typing import Any
from typing import TypeVar

import requests
import requests.exceptions

from FTB.ConfigurationFiles import ConfigurationFiles  # noqa


LOG = logging.getLogger(__name__)
RetType = TypeVar("RetType")


def remote_checks(wrapped: Callable[..., RetType]) -> Callable[..., RetType]:
    '''Decorator to perform error checks before using remote features'''
    @functools.wraps(wrapped)
    def decorator(self: Reporter, *args: str, **kwargs: str) -> RetType:
        if not self.serverHost:
            raise RuntimeError("Must specify serverHost (configuration property: serverhost) to use remote features.")
        if not self.serverAuthToken:
            raise RuntimeError("Must specify serverAuthToken (configuration property: serverauthtoken) "
                               "to use remote features.")
        if not self.tool:
            raise RuntimeError("Must specify tool (configuration property: tool) to use remote features.")
        return wrapped(self, *args, **kwargs)
    return decorator


def signature_checks(wrapped: Callable[..., RetType]) -> Callable[..., RetType]:
    '''Decorator to perform error checks before using signature features'''
    @functools.wraps(wrapped)
    def decorator(self: Reporter, *args: str, **kwargs: str) -> RetType:
        if not self.sigCacheDir:
            raise RuntimeError("Must specify sigCacheDir (configuration property: sigdir) to use signatures.")
        return wrapped(self, *args, **kwargs)
    return decorator


def requests_retry(wrapped: Callable[..., Any]) -> Callable[..., Any]:
    '''Wrapper around requests methods that retries up to 2 minutes if it's likely that the response codes indicate a
    temporary error'''
    @functools.wraps(wrapped)
    def wrapper(*args: str, **kwds: Any) -> Any:
        success = kwds.pop("expected")
        current_timeout = 2
        while True:
            try:
                response = wrapped(*args, **kwds)
            except requests.exceptions.ConnectionError as exc:
                if current_timeout <= 64:
                    LOG.warning("in %s, %s, retrying...", wrapped.__name__, exc)
                    time.sleep(current_timeout)
                    current_timeout *= 2
                    continue
                raise

            if response.status_code != success:
                # Allow for a total sleep time of up to 2 minutes if it's
                # likely that the response codes indicate a temporary error
                retry_codes = [500, 502, 503, 504]
                if response.status_code in retry_codes and current_timeout <= 64:
                    LOG.warning("in %s, server returned %s, retrying...", wrapped.__name__, response.status_code)
                    time.sleep(current_timeout)
                    current_timeout *= 2
                    continue
                raise Reporter.serverError(response)
            return response
    return wrapper


class Reporter(ABC):
    def __init__(
        self,
        sigCacheDir: str | None = None,
        serverHost: str | None = None,
        serverPort: int | None = None,
        serverProtocol: str | None = None,
        serverAuthToken: str | None = None,
        clientId: str | None = None,
        tool: str | None = None,
    ):
        '''
        Initialize the Reporter. This constructor will also attempt to read
        a configuration file to populate any missing properties that have not
        been passed to this constructor.

        @param sigCacheDir: Directory to be used for caching signatures
        @param serverHost: Server host to contact for refreshing signatures
        @param serverPort: Server port to use when contacting server
        @param serverAuthToken: Token for server authentication
        @param clientId: Client ID stored in the server when submitting issues
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
        globalConfigFile = os.getenv(
            "FM_CONFIG_PATH",
            os.path.join(os.path.expanduser("~"), ".fuzzmanagerconf"),
        )
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

    def get(self, *args: Any, **kwds: Any) -> Any:
        """requests.get, with added support for FuzzManager authentication and retry on 5xx errors.

        @type expected: int
        @param expected: HTTP status code for successful response (default: requests.codes["ok"])
        """
        kwds.setdefault("expected", requests.codes["ok"])
        kwds.setdefault("headers", {}).update({"Authorization": "Token %s" % self.serverAuthToken})
        return requests_retry(self._session.get)(*args, **kwds)

    def post(self, *args: Any, **kwds: Any) -> Any:
        """requests.post, with added support for FuzzManager authentication and retry on 5xx errors.

        @type expected: int
        @param expected: HTTP status code for successful response (default: requests.codes["created"])
        """
        kwds.setdefault("expected", requests.codes["created"])
        kwds.setdefault("headers", {}).update({"Authorization": "Token %s" % self.serverAuthToken})
        return requests_retry(self._session.post)(*args, **kwds)

    def patch(self, *args: Any, **kwds: Any) -> Any:
        """requests.patch, with added support for FuzzManager authentication and retry on 5xx errors.

        @type expected: int
        @param expected: HTTP status code for successful response (default: requests.codes["created"])
        """
        kwds.setdefault("expected", requests.codes["ok"])
        kwds.setdefault("headers", {}).update({"Authorization": "Token %s" % self.serverAuthToken})
        return requests_retry(self._session.patch)(*args, **kwds)

    @staticmethod
    def serverError(response: requests.Response) -> RuntimeError:
        return RuntimeError("Server unexpectedly responded with status code %s: %s" %
                            (response.status_code, response.text))
