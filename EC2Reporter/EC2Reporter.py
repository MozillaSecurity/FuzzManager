#!/usr/bin/env python
# encoding: utf-8
'''
EC2Reporter -- Simple EC2 status reporting tool for EC2SpotManager

Provide process and class level interfaces to send simple textual
status reports to EC2SpotManager.

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''

# Ensure print() compatibility with Python 3
from __future__ import print_function

import argparse
import os
import platform
import requests
import sys

BASE_DIR = os.path.dirname(os.path.realpath(__file__))
FTB_PATH = os.path.abspath(os.path.join(BASE_DIR, ".."))
sys.path += [FTB_PATH]

from FTB.ConfigurationFiles import ConfigurationFiles

__all__ = []
__version__ = 0.1
__date__ = '2014-10-01'
__updated__ = '2014-10-01'

def remote_checks(f):
    'Decorator to perform error checks before using remote features'
    def decorator(self, *args, **kwargs):
        if not self.serverHost:
            raise RuntimeError("Must specify serverHost (configuration property: serverhost) to use remote features.")
        if not self.serverHost:
            raise RuntimeError("Must specify serverAuthToken (configuration property: serverauthtoken) to use remote features.")
        if not self.clientId:
            raise RuntimeError("Must specify clientId (configuration property: clientid) to use remote features.")
        return f(self, *args, **kwargs)
    return decorator

class EC2Reporter():
    def __init__(self, serverHost=None, serverPort=None,
                 serverProtocol=None, serverAuthToken=None,
                 clientId=None):
        '''
        Initialize the Reporter. This constructor will also attempt to read
        a configuration file to populate any missing properties that have not
        been passed to this constructor.

        @type serverHost: string
        @param serverHost: Server host to contact for refreshing signatures
        @type serverPort: int
        @param serverPort: Server port to use when contacting server
        @type serverAuthToken: string
        @param serverAuthToken: Token for server authentication
        @type clientId: string
        @param clientId: Client ID stored in the server when submitting issues
        '''
        self.serverHost = serverHost
        self.serverPort = serverPort
        self.serverProtocol = serverProtocol
        self.serverAuthToken = serverAuthToken
        self.clientId = clientId

        # Now search for the global configuration file. If it exists, read its contents
        # and set all Collector settings that haven't been explicitely set by the user.
        globalConfigFile = os.path.join(os.path.expanduser("~"), ".fuzzmanagerconf")
        if os.path.exists(globalConfigFile):
            configInstance = ConfigurationFiles([ globalConfigFile ])
            globalConfig = configInstance.mainConfig

            if self.serverHost == None and "serverhost" in globalConfig:
                self.serverHost = globalConfig["serverhost"]

            if self.serverPort == None and "serverport" in globalConfig:
                self.serverPort = globalConfig["serverport"]

            if self.serverProtocol == None and "serverproto" in globalConfig:
                self.serverProtocol = globalConfig["serverproto"]

            if self.serverAuthToken == None:
                if "serverauthtoken" in globalConfig:
                    self.serverAuthToken = globalConfig["serverauthtoken"]
                elif "serverauthtokenfile" in globalConfig:
                    with open(globalConfig["serverauthtokenfile"]) as f:
                        self.serverAuthToken = f.read().rstrip()

            if self.clientId == None and "clientid" in globalConfig:
                self.clientId = globalConfig["clientid"]

        # Set some defaults that we can't set through default arguments, otherwise
        # they would overwrite configuration file settings
        if self.serverProtocol == None:
            self.serverProtocol = "https"

        # Try to be somewhat intelligent about the default port, depending on protocol
        if self.serverPort == None:
            if self.serverProtocol == "https":
                self.serverPort = 433
            else:
                self.serverPort = 80

        if self.serverHost != None and self.clientId == None:
            self.clientId = platform.node()

    @remote_checks
    def report(self, text):
        '''
        Send textual report to server, overwriting any existing reports.
        
        @type text: string
        @param text: Report text to send
        '''
        url = "%s://%s:%s/ec2spotmanager/rest/report/" % (self.serverProtocol, self.serverHost, self.serverPort)

        # Serialize our report information
        data = {}

        data["client"] = self.clientId
        data["status_data"] = text

        response = requests.post(url, data, headers=dict(Authorization="Token %s" % self.serverAuthToken))

        if response.status_code != requests.codes["created"]:
            raise self.__serverError(response)

    @staticmethod
    def __serverError(response):
        return RuntimeError("Server unexpectedly responded with status code %s: %s" %
                            (response.status_code, response.text))

def main(argv=None):
    '''Command line options.'''

    program_name = os.path.basename(sys.argv[0])
    program_version = "v%s" % __version__
    program_build_date = "%s" % __updated__

    program_version_string = '%%prog %s (%s)' % (program_version, program_build_date)

    if argv is None:
        argv = sys.argv[1:]

    # setup argparser
    parser = argparse.ArgumentParser()

    parser.add_argument('--version', action='version', version=program_version_string)

    # Actions
    parser.add_argument("--report", dest="report", type=str, help="Submit the given textual report", metavar="TEXT")
    parser.add_argument("--report-from-file", dest="report_file", type=str, help="Submit the given file as textual report", metavar="FILE")

    # Settings
    parser.add_argument("--serverhost", dest="serverhost", help="Server hostname for remote signature management", metavar="HOST")
    parser.add_argument("--serverport", dest="serverport", type=int, help="Server port to use", metavar="PORT")
    parser.add_argument("--serverproto", dest="serverproto", help="Server protocol to use (default is https)", metavar="PROTO")
    parser.add_argument("--serverauthtokenfile", dest="serverauthtokenfile", help="File containing the server authentication token", metavar="FILE")
    parser.add_argument("--clientid", dest="clientid", help="Client ID to use when submitting issues", metavar="ID")

    if len(argv) == 0:
        parser.print_help()
        return 2

    # process options
    opts = parser.parse_args(argv)

    # Check that one action is specified
    actions = [ "report", "report_file" ]

    haveAction = False
    for action in actions:
        if getattr(opts, action):
            if haveAction:
                print("Error: Cannot specify multiple actions at the same time", file=sys.stderr)
                return 2
            haveAction = True
    if not haveAction:
        print("Error: Must specify an action", file=sys.stderr)
        return 2

    serverauthtoken = None
    if opts.serverauthtokenfile:
        with open(opts.serverauthtokenfile) as f:
            serverauthtoken = f.read().rstrip()

    reporter = EC2Reporter(opts.serverhost, opts.serverport, opts.serverproto, serverauthtoken, opts.clientid)
    report = None

    if opts.report_file:
        with open(opts.report_file) as f:
            report = f.read()
    else:
        report = opts.report

    reporter.report(report)
    return 0

if __name__ == "__main__":
    sys.exit(main())
