#!/usr/bin/env python3
"""
TaskStatusReporter -- Simple status reporting tool for TaskManager

Provide process and class level interfaces to send simple textual
status reports to TaskManager.

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    jschwartzentruber@mozilla.com
"""
import argparse
import functools
import os
import random
import sys
import time
from pathlib import Path

import requests
from fasteners import InterProcessLock

from FTB.ConfigurationFiles import ConfigurationFiles  # noqa
from Reporter.Reporter import Reporter, ServerError, remote_checks, sentry_init

__all__ = []
__version__ = 0.1
__date__ = "2020-04-24"
__updated__ = "2025-04-08"


class TaskStatusReporter(Reporter):
    @functools.wraps(Reporter.__init__)
    def __init__(self, *args, **kwargs):
        kwargs.setdefault(
            "tool", "N/A"
        )  # tool is required by remote_checks, but unused by TaskStatusReporter
        super().__init__(*args, **kwargs)

    @staticmethod
    def write_report_file(path, text):
        """
        Write textual report to a file, ensuring that interprocess locking is used.
        This ensures that `--keep-reporting` will not conflict with file writes.

        @type path: Path
        @param path: File path to write report to.

        @type text: string
        @param text: Report text to write
        """
        report_file = Path(path)

        with InterProcessLock(f"{report_file}.lock"):
            report_file.write_text(text)

    @remote_checks
    def report(self, text):
        """
        Send textual report to server, overwriting any existing reports.

        @type text: string
        @param text: Report text to send
        """
        url = "{}://{}:{}/taskmanager/rest/tasks/update_status/".format(
            self.serverProtocol,
            self.serverHost,
            self.serverPort,
        )
        # Serialize our report information
        data = {
            "client": self.clientId,
            "status_data": text,
        }

        self.post(url, data, expected=requests.codes["ok"], max_sleep=0)


def main(argv=None):
    """Command line options."""
    sentry_init()

    # setup argparser
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--version",
        action="version",
        version=f"{os.path.basename(__file__)} v{__version__} ({__updated__})",
    )

    # Actions
    action_group = parser.add_argument_group(
        "Actions", "A single action must be selected."
    )
    actions = action_group.add_mutually_exclusive_group(required=True)
    actions.add_argument(
        "--report",
        help="Submit the given textual report",
        metavar="TEXT",
    )
    actions.add_argument(
        "--report-from-file",
        dest="report_file",
        type=Path,
        help="Submit the given file as textual report",
        metavar="FILE",
    )

    # Options
    parser.add_argument(
        "--keep-reporting",
        default=0,
        type=int,
        help="Keep reporting from the specified file with specified interval",
        metavar="SECONDS",
    )
    parser.add_argument(
        "--random-offset",
        default=0,
        type=int,
        help="Random offset for the reporting interval (+/-)",
        metavar="SECONDS",
    )

    # Settings
    parser.add_argument(
        "--serverhost",
        help="Server hostname for remote signature management",
        metavar="HOST",
    )
    parser.add_argument(
        "--serverport",
        type=int,
        help="Server port to use",
        metavar="PORT",
    )
    parser.add_argument(
        "--serverproto",
        help="Server protocol to use (default is https)",
        metavar="PROTO",
    )
    parser.add_argument(
        "--serverauthtokenfile",
        type=Path,
        help="File containing the server authentication token",
        metavar="FILE",
    )
    parser.add_argument(
        "--clientid",
        help="Client ID to use when submitting issues",
        metavar="ID",
    )

    # process options
    opts = parser.parse_args(argv)

    if opts.keep_reporting and opts.report_file is None:
        print(
            "Error: --keep-reporting is only valid with --report-from-file",
            file=sys.stderr,
        )
        return 2

    serverauthtoken = None
    if opts.serverauthtokenfile is not None:
        serverauthtoken = opts.serverauthtokenfile.read_text().rstrip()

    reporter = TaskStatusReporter(
        opts.serverhost,
        opts.serverport,
        opts.serverproto,
        serverauthtoken,
        opts.clientid,
    )
    report = None

    if opts.report_file is not None:
        if opts.keep_reporting:
            if opts.random_offset > 0:
                random.seed(reporter.clientId)

            lock = InterProcessLock(f"{opts.report_file}.lock")
            while True:
                if opts.report_file.is_file():
                    with lock:
                        report = opts.report_file.read_text()

                    try:
                        reporter.report(report)
                    except ServerError as e:
                        # Ignore errors if the server is temporarily unavailable
                        print(f"Failed to contact server: {e}", file=sys.stderr)

                random_offset = 0
                if opts.random_offset:
                    random_offset = random.randint(
                        -opts.random_offset, opts.random_offset
                    )
                time.sleep(opts.keep_reporting + random_offset)
        else:
            with InterProcessLock(f"{opts.report_file}.lock"):
                report = opts.report_file.read_text()
    else:
        report = opts.report

    reporter.report(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
