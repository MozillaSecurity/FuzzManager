"""
Reporter -- Abstract base class for all reporters that use FuzzManager's config file

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
"""

import functools
import logging
import os
import platform
import time
from abc import ABC

import requests
import requests.exceptions

from FTB.ConfigurationFiles import ConfigurationFiles

LOG = logging.getLogger(__name__)


# Inheriting from RuntimeError because of legacy code.
# All of these exceptions used to be RuntimeError.
class ReporterException(RuntimeError):
    """Base class for Reporter exceptions."""


class ConfigurationError(ReporterException):
    """Error type for configuration problems preventing Reporter from functioning."""


class ServerError(ReporterException):
    """Communication errors encountered by Reporter during operation."""


class InvalidDataError(ReporterException):
    """Reporter data validation failures."""


def remote_checks(wrapped):
    """Decorator to perform error checks before using remote features"""

    @functools.wraps(wrapped)
    def decorator(self, *args, **kwargs):
        if not self.serverHost:
            raise ConfigurationError(
                "Must specify serverHost (configuration property: serverhost) to use "
                "remote features."
            )
        if not self.serverAuthToken:
            raise ConfigurationError(
                "Must specify serverAuthToken (configuration property: "
                "serverauthtoken) to use remote features."
            )
        if not self.tool:
            raise ConfigurationError(
                "Must specify tool (configuration property: tool) to use remote "
                "features."
            )
        return wrapped(self, *args, **kwargs)

    return decorator


def signature_checks(wrapped):
    """Decorator to perform error checks before using signature features"""

    @functools.wraps(wrapped)
    def decorator(self, *args, **kwargs):
        if not self.sigCacheDir:
            raise ConfigurationError(
                "Must specify sigCacheDir (configuration property: sigdir) to use "
                "signatures."
            )
        return wrapped(self, *args, **kwargs)

    return decorator


def requests_retry(wrapped):
    """Wrapper around requests methods that retries up to 2 minutes if it's likely that
    the response codes indicate a temporary error"""

    @functools.wraps(wrapped)
    def wrapper(*args, **kwds):
        success = kwds.pop("expected")
        # max_sleep is the upper limit for exponential backoff,
        # which begins at 2s and doubles each retry
        max_sleep = kwds.pop("max_sleep", 64)
        current_timeout = 2
        while True:
            try:
                response = wrapped(*args, **kwds)
            except requests.exceptions.ConnectionError as exc:
                if current_timeout <= max_sleep:
                    LOG.warning("in %s, %s, retrying...", wrapped.__name__, exc)
                    time.sleep(current_timeout)
                    current_timeout *= 2
                    continue
                raise ServerError(f"maximum timeout exceeded: {exc}") from None

            if response.status_code != success:
                # Allow for a total sleep time of up to 2 minutes if it's
                # likely that the response codes indicate a temporary error
                retry_codes = [429, 500, 502, 503, 504]
                if response.status_code in retry_codes and current_timeout <= max_sleep:
                    LOG.warning(
                        "in %s, server returned %s, retrying...",
                        wrapped.__name__,
                        response.status_code,
                    )
                    time.sleep(current_timeout)
                    current_timeout *= 2
                    continue
                raise ServerError(
                    "Server unexpectedly responded with status code "
                    f"{response.status_code}: {response.text}"
                )
            return response

    return wrapper


class Reporter(ABC):
    def __init__(
        self,
        sigCacheDir=None,
        serverHost=None,
        serverPort=None,
        serverProtocol=None,
        serverAuthToken=None,
        clientId=None,
        tool=None,
    ):
        """
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
        """
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

    def get(self, *args, **kwds):
        """requests.get, with added support for FuzzManager authentication and retry on
        5xx errors.

        @type expected: int
        @param expected: HTTP status code for successful response
                         (default: requests.codes["ok"])
        """
        kwds.setdefault("expected", requests.codes["ok"])
        kwds.setdefault("headers", {}).update(
            {"Authorization": f"Token {self.serverAuthToken}"}
        )
        return requests_retry(self._session.get)(*args, **kwds)

    def post(self, *args, **kwds):
        """requests.post, with added support for FuzzManager authentication and retry on
        5xx errors.

        @type expected: int
        @param expected: HTTP status code for successful response
                         (default: requests.codes["created"])
        """
        kwds.setdefault("expected", requests.codes["created"])
        kwds.setdefault("headers", {}).update(
            {"Authorization": f"Token {self.serverAuthToken}"}
        )
        return requests_retry(self._session.post)(*args, **kwds)

    def patch(self, *args, **kwds):
        """requests.patch, with added support for FuzzManager authentication and retry
        on 5xx errors.

        @type expected: int
        @param expected: HTTP status code for successful response
                         (default: requests.codes["created"])
        """
        kwds.setdefault("expected", requests.codes["ok"])
        kwds.setdefault("headers", {}).update(
            {"Authorization": f"Token {self.serverAuthToken}"}
        )
        return requests_retry(self._session.patch)(*args, **kwds)
