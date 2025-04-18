#!/usr/bin/env python3
"""
CovReporter -- Coverage reporting client for CoverageManager

Provide process and class level interfaces to post-process and submit
coverage data to CoverageManager.

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
"""
import argparse
import json
import os
import sys

from FTB import CoverageHelper
from Reporter.Reporter import InvalidDataError, Reporter, remote_checks

__all__ = []
__version__ = 0.1
__date__ = "2017-07-10"
__updated__ = "2025-04-08"


class CovReporter(Reporter):
    def __init__(
        self,
        serverHost=None,
        serverPort=None,
        serverProtocol=None,
        serverAuthToken=None,
        clientId=None,
        tool=None,
        repository=None,
    ):
        """
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
        @param clientId: Client ID stored in the server when submitting
        @type tool: string
        @param tool: Name of the tool that created this coverage
        @type repository: string
        @param repository: Name of the repository that this coverage was measured on
        """

        # Call abstract base class to handle configuration file
        Reporter.__init__(
            self,
            sigCacheDir=None,
            serverHost=serverHost,
            serverPort=serverPort,
            serverProtocol=serverProtocol,
            serverAuthToken=serverAuthToken,
            clientId=clientId,
            tool=tool,
        )

        self.repository = repository

    @remote_checks
    def submit(
        self, coverage, preprocessed=False, version=None, description="", stats=None
    ):
        """
        Send coverage data to server.

        @type coverage: dict
        @param coverage: Coverage Data

        @type covformat: int
        @param covformat: Format of the coverage data (COVERALLS or COVMAN).

        @type version: dict
        @param version: A dictionary containing keys 'revision' and 'branch', just
                        as returned by version_info_from_coverage_data. If left
                        empty, the implementation will attempt to extract the
                        information from the coverage data itself.

        @type description: string
        @param description: Optional description for this coverage data

        @type stats: dict
        @param stats: An optional stats object as returned by create_combined_coverage
        """
        url = "{}://{}:{}/covmanager/rest/collections/".format(
            self.serverProtocol,
            self.serverHost,
            self.serverPort,
        )

        if version is None:
            # Use version information extracted from coverage data
            version = CovReporter.version_info_from_coverage_data(coverage)

        if not preprocessed:
            # Preprocess our coverage data to transform it into the server-side
            # format unless the data has already been preprocessed before.
            coverage = CovReporter.preprocess_coverage_data(coverage)

        if stats is not None:
            # These variables are mainly for debugging purposes. We count the number
            # of warnings we encounter during merging, which are mostly due to
            # bugs in GCOV. These statistics are included in the report description
            # to track the status of these bugs.
            if len(description) > 0:
                description += " "
            description += "(dv1:{},{},{})".format(
                stats["null_coverable_count"],
                stats["length_mismatch_count"],
                stats["coverable_mismatch_count"],
            )

        # Serialize our coverage information
        data = {}

        data["repository"] = self.repository
        data["tools"] = self.tool
        data["client"] = self.clientId
        data["coverage"] = json.dumps(coverage, separators=(",", ":"))
        data["description"] = description
        data.update(version)

        self.post(url, data)

    @staticmethod
    def preprocess_coverage_data(coverage):
        """
        Preprocess the given coverage data.

        Preprocessing includes structuring the coverage data by directory
        for better performance as well as computing coverage summaries per directory.

        @type coverage: dict
        @param coverage: Coverage Data

        @rtype dict
        @return Preprocessed Coverage Data
        """

        ret = {"children": {}}

        if "source_files" in coverage:
            # Coveralls format
            source_files = coverage["source_files"]

            # Process every source file and store the coverage data in our tree
            # structure
            for source_file in source_files:
                # Split the filename into path parts and file part
                name = source_file["name"]
                name_parts = name.split("/")
                path_parts = name_parts[:-1]
                file_part = name_parts[-1]

                # Start at the top of the tree for the path walking
                ptr = ret["children"]

                # Walk the tree down, one path part at a time and create parts
                # on the fly if they don't exist yet in our tree.
                for path_part in path_parts:
                    if path_part not in ptr:
                        ptr[path_part] = {"children": {}}

                    ptr = ptr[path_part]["children"]

                ptr[file_part] = {
                    "coverage": [
                        -1 if x is None else x for x in source_file["coverage"]
                    ]
                }

        else:
            raise InvalidDataError("Unknown coverage format")

        # Now we need to calculate the coverage summaries (lines total and covered)
        # for each subtree in the tree. We can do this easily by using a recursive
        # definition.
        CoverageHelper.calculate_summary_fields(ret)

        return ret

    @staticmethod
    def version_info_from_coverage_data(coverage):
        """
        Extract various version fields from the given coverage data.

        Certain coverage data formats store version information in the data,
        e.g. the revision or the branch. This method is used by the submit
        method to extract this information.

        The extracted fields currently include:

        revision
        branch

        @type coverage: string
        @param coverage: Coverage Data

        @return Dictionary with version data
        @rtype dict
        """

        ret = {}

        if "git" in coverage and "head" in coverage["git"]:
            ret["revision"] = coverage["git"]["head"]["id"]
            ret["branch"] = coverage["git"]["branch"]
            return ret
        else:
            raise InvalidDataError("Unknown coverage format")

    @staticmethod
    def create_combined_coverage(coverage_files, version=None):
        """
        Read coverage data from multiple files and return a single dictionary
        containing the merged data (already preprocessed).

        @type coverage_files: list
        @param coverage_files: List of filenames containing coverage data
        @type version: dict
        @param version: Dictionary containing branch and revision

        @return Dictionary with combined coverage data, version information and debug
                statistics
        @rtype tuple(dict,dict,dict)
        """
        ret = None
        stats = None

        # Only preprocess report if version was not supplied
        needs_preprocess = version is None

        for coverage_file in coverage_files:
            with open(coverage_file) as f:
                coverage = json.load(f)

                if version is None:
                    version = CovReporter.version_info_from_coverage_data(coverage)

                if needs_preprocess:
                    coverage = CovReporter.preprocess_coverage_data(coverage)

                if ret is None:
                    ret = coverage
                else:
                    merge_stats = CoverageHelper.merge_coverage_data(ret, coverage)
                    if stats is None:
                        stats = merge_stats
                    else:
                        for k in merge_stats:
                            if k in stats:
                                stats[k] += merge_stats[k]

        return (ret, version, stats)


def main(argv=None):
    """Command line options."""

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
        "--submit", help="Submit the given file as coverage data", metavar="FILE"
    )
    actions.add_argument(
        "--multi-submit",
        action="store_true",
        help="Submit multiple files (specified last on the command line)",
    )

    # Generic Settings
    parser.add_argument(
        "--serverhost",
        help="Server hostname for remote signature management",
        metavar="HOST",
    )
    parser.add_argument(
        "--serverport", type=int, help="Server port to use", metavar="PORT"
    )
    parser.add_argument(
        "--serverproto",
        help="Server protocol to use (default is https)",
        metavar="PROTO",
    )
    parser.add_argument(
        "--serverauthtokenfile",
        help="File containing the server authentication token",
        metavar="FILE",
    )
    parser.add_argument(
        "--clientid",
        help="Client ID to use when submitting coverage data",
        metavar="ID",
    )
    parser.add_argument(
        "--tool", help="Name of the tool that generated this coverage", metavar="NAME"
    )

    # Coverage specific settings
    parser.add_argument(
        "--repository",
        help="Name of the repository this coverage was measured on",
        metavar="NAME",
    )
    parser.add_argument(
        "--description",
        default="",
        help="Description for this coverage collection",
        metavar="NAME",
    )
    parser.add_argument(
        "--preprocessed",
        help="Coverage report is already preprocessed",
        action="store_true",
    )

    parser.add_argument(
        "--branch",
        help="Name of the branch this coverage was measured on",
        metavar="NAME",
    )
    parser.add_argument(
        "--revision", help="Revision this coverage was measured on", metavar="NAME"
    )

    parser.add_argument("rargs", nargs=argparse.REMAINDER)

    # process options
    opts = parser.parse_args(argv)

    version = None
    if opts.preprocessed:
        if None in (opts.branch, opts.revision):
            print(
                "Error: Must specify --branch and --revision when disabling the "
                "preprocessor",
                file=sys.stderr,
            )
            return 2

        version = {"revision": opts.revision, "branch": opts.branch}

    serverauthtoken = None
    if opts.serverauthtokenfile:
        with open(opts.serverauthtokenfile) as f:
            serverauthtoken = f.read().rstrip()

    reporter = CovReporter(
        opts.serverhost,
        opts.serverport,
        opts.serverproto,
        serverauthtoken,
        opts.clientid,
        opts.tool,
        opts.repository,
    )

    if opts.submit or opts.multi_submit:
        if not opts.repository:
            print(
                "Error: Must specify --repository when submitting coverage",
                file=sys.stderr,
            )
            return 2

        if opts.submit:
            with open(opts.submit) as f:
                coverage = json.load(f)
            reporter.submit(
                coverage,
                opts.preprocessed,
                version=version,
                description=opts.description,
            )
        else:
            if not opts.rargs:
                print(
                    "Error: Must specify at least one file with --multi-submit",
                    file=sys.stderr,
                )
                return 2

            (coverage, version, stats) = CovReporter.create_combined_coverage(
                opts.rargs, version
            )
            reporter.submit(
                coverage,
                preprocessed=True,
                version=version,
                description=opts.description,
                stats=stats,
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
