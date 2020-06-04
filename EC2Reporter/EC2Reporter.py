#!/usr/bin/env python3
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
import functools
import os
import random
import sys
import time

from fasteners import InterProcessLock
import requests

from FTB.ConfigurationFiles import ConfigurationFiles  # noqa
from Reporter.Reporter import Reporter, remote_checks  # noqa

__all__ = []
__version__ = 0.1
__date__ = '2014-10-01'
__updated__ = '2014-10-01'


class EC2Reporter(Reporter):
    @functools.wraps(Reporter.__init__)
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('tool', 'N/A')  # tool is required by remote_checks, but unused by EC2Reporter
        super(EC2Reporter, self).__init__(*args, **kwargs)

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

        self.post(url, data)

    @remote_checks
    def cycle(self, poolid):
        '''
        Cycle the pool with the given id.

        @type poolid: int
        @param poolid: ID of the pool to cycle
        '''
        url = "%s://%s:%s/ec2spotmanager/rest/pool/%s/cycle/" % (self.serverProtocol, self.serverHost, self.serverPort,
                                                                 poolid)

        self.post(url, {}, expected=requests.codes["ok"])

    @remote_checks
    def disable(self, poolid):
        '''
        Disable the pool with the given id.

        @type poolid: int
        @param poolid: ID of the pool to disable
        '''
        url = "%s://%s:%s/ec2spotmanager/rest/pool/%s/disable/" % (self.serverProtocol, self.serverHost,
                                                                   self.serverPort, poolid)

        self.post(url, {}, expected=requests.codes["ok"])

    @remote_checks
    def enable(self, poolid):
        '''
        Enable the pool with the given id.

        @type poolid: int
        @param poolid: ID of the pool to enable
        '''
        url = "%s://%s:%s/ec2spotmanager/rest/pool/%s/enable/" % (self.serverProtocol, self.serverHost,
                                                                  self.serverPort, poolid)

        self.post(url, {}, expected=requests.codes["ok"])


def main(argv=None):
    '''Command line options.'''

    # setup argparser
    parser = argparse.ArgumentParser()

    parser.add_argument('--version', action='version', version='%s v%s (%s)' %
                        (os.path.basename(__file__), __version__, __updated__))

    # Actions
    action_group = parser.add_argument_group("Actions", "A single action must be selected.")
    actions = action_group.add_mutually_exclusive_group(required=True)
    actions.add_argument("--report", dest="report", type=str, help="Submit the given textual report", metavar="TEXT")
    actions.add_argument("--report-from-file", dest="report_file", type=str,
                         help="Submit the given file as textual report", metavar="FILE")
    actions.add_argument("--cycle", dest="cycle", type=str, help="Cycle the pool with the given ID", metavar="ID")
    actions.add_argument("--disable", dest="disable", type=str, help="Disable the pool with the given ID", metavar="ID")
    actions.add_argument("--enable", dest="enable", type=str, help="Enable the pool with the given ID", metavar="ID")

    # Options
    parser.add_argument("--keep-reporting", dest="keep_reporting", default=0, type=int,
                        help="Keep reporting from the specified file with specified interval", metavar="SECONDS")
    parser.add_argument("--random-offset", dest="random_offset", default=0, type=int,
                        help="Random offset for the reporting interval (+/-)", metavar="SECONDS")

    # Settings
    parser.add_argument("--serverhost", dest="serverhost",
                        help="Server hostname for remote signature management", metavar="HOST")
    parser.add_argument("--serverport", dest="serverport", type=int, help="Server port to use", metavar="PORT")
    parser.add_argument("--serverproto", dest="serverproto",
                        help="Server protocol to use (default is https)", metavar="PROTO")
    parser.add_argument("--serverauthtokenfile", dest="serverauthtokenfile",
                        help="File containing the server authentication token", metavar="FILE")
    parser.add_argument("--clientid", dest="clientid", help="Client ID to use when submitting issues", metavar="ID")

    # process options
    opts = parser.parse_args(argv)

    if opts.keep_reporting and not opts.report_file:
        print("Error: --keep-reporting is only valid with --report-from-file", file=sys.stderr)
        return 2

    serverauthtoken = None
    if opts.serverauthtokenfile:
        with open(opts.serverauthtokenfile) as f:
            serverauthtoken = f.read().rstrip()

    reporter = EC2Reporter(opts.serverhost, opts.serverport, opts.serverproto, serverauthtoken, opts.clientid)
    report = None

    if opts.cycle:
        reporter.cycle(opts.cycle)
        return 0
    elif opts.enable:
        reporter.enable(opts.enable)
        return 0
    elif opts.disable:
        reporter.disable(opts.disable)
        return 0
    elif opts.report_file:
        if opts.keep_reporting:
            if opts.random_offset > 0:
                random.seed(reporter.clientId)

            lock = InterProcessLock(opts.report_file + ".lock")
            while True:
                if os.path.exists(opts.report_file):
                    if not lock.acquire(timeout=opts.keep_reporting):
                        continue
                    try:
                        with open(opts.report_file) as f:
                            report = f.read()
                        try:
                            reporter.report(report)
                        except RuntimeError as e:
                            # Ignore errors if the server is temporarily unavailable
                            print("Failed to contact server: %s" % e, file=sys.stderr)
                    finally:
                        lock.release()

                random_offset = 0
                if opts.random_offset:
                    random_offset = random.randint(-opts.random_offset, opts.random_offset)
                time.sleep(opts.keep_reporting + random_offset)
        else:
            with open(opts.report_file) as f:
                report = f.read()
    else:
        report = opts.report

    reporter.report(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
