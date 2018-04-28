#!/usr/bin/env python
# encoding: utf-8
'''
CovReporter -- Coverage reporting client for CoverageManager

Provide process and class level interfaces to post-process and submit
coverage data to CoverageManager.

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
import json
import os
import sys

from Reporter.Reporter import remote_checks, Reporter  # noqa

__all__ = []
__version__ = 0.1
__date__ = '2017-07-10'
__updated__ = '2017-07-10'

# Debugging variables to keep track of GCOV errors
null_coverable_count = 0
length_mismatch_count = 0
coverable_mismatch_count = 0


class CovReporter(Reporter):
    def __init__(self, serverHost=None, serverPort=None,
                 serverProtocol=None, serverAuthToken=None,
                 clientId=None, tool=None, repository=None):
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
        @param clientId: Client ID stored in the server when submitting
        @type tool: string
        @param tool: Name of the tool that created this coverage
        @type repository: string
        @param repository: Name of the repository that this coverage was measured on
        '''

        # Call abstract base class to handle configuration file
        Reporter.__init__(self,
                          sigCacheDir=None,
                          serverHost=serverHost,
                          serverPort=serverPort,
                          serverProtocol=serverProtocol,
                          serverAuthToken=serverAuthToken,
                          clientId=clientId,
                          tool=tool)

        self.repository = repository

    @remote_checks
    def submit(self, coverage, preprocessed=False, version=None, description=""):
        '''
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
        @param description: Optional descripton for this coverage data
        '''
        url = "%s://%s:%s/covmanager/rest/collections/" % (self.serverProtocol, self.serverHost, self.serverPort)

        if version is None:
            # Use version information extracted from coverage data
            version = CovReporter.version_info_from_coverage_data(coverage)

        if not preprocessed:
            # Preprocess our coverage data to transform it into the server-side
            # format unless the data has already been preprocessed before.
            coverage = CovReporter.preprocess_coverage_data(coverage)

        if len(description) > 0:
            description += " "
        description += "(dv1:%s,%s,%s)" % (null_coverable_count, length_mismatch_count, coverable_mismatch_count)

        # Serialize our coverage information
        data = {}

        data["repository"] = self.repository
        data["tools"] = self.tool
        data["client"] = self.clientId
        data["coverage"] = json.dumps(coverage, separators=(',', ':'))
        data["description"] = description
        data.update(version)

        self.post(url, data)

    @staticmethod
    def preprocess_coverage_data(coverage):
        '''
        Preprocess the given coverage data.

        Preprocessing includes structuring the coverage data by directory
        for better performance as well as computing coverage summaries per directory.

        @type coverage: dict
        @param coverage: Coverage Data

        @rtype dict
        @return Preprocessed Coverage Data
        '''

        ret = {"children": {}}

        if "source_files" in coverage:
            # Coveralls format
            source_files = coverage["source_files"]

            # Process every source file and store the coverage data in our tree structure
            for source_file in source_files:

                # Split the filename into path parts and file part
                name = source_file["name"]
                name_parts = name.split(os.sep)
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
                    "coverage": [-1 if x is None else x for x in source_file["coverage"]]
                }

        else:
            raise RuntimeError("Unknown coverage format")

        # Now we need to calculate the coverage summaries (lines total and covered)
        # for each subtree in the tree. We can do this easily by using a recursive
        # definition.
        CovReporter.__calculate_summary_fields(ret)

        return ret

    @staticmethod
    def version_info_from_coverage_data(coverage):
        '''
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
        '''

        ret = {}

        if "git" in coverage and "head" in coverage["git"]:
            ret["revision"] = coverage["git"]["head"]["id"]
            ret["branch"] = coverage["git"]["branch"]
            return ret
        else:
            raise RuntimeError("Unknown coverage format")

    @staticmethod
    def create_combined_coverage(coverage_files):
        '''
        Read coverage data from multiple files and return a single dictionary
        containing the merged data (already preprocessed).

        @type coverage_files: list
        @param coverage_files: List of filenames containing coverage data

        @return Dictionary with combined coverage data and version information
        @rtype tuple(dict,dict)
        '''

        ret = None
        version = None

        for coverage_file in coverage_files:
            with open(coverage_file) as f:
                coverage = json.load(f)

                if version is None:
                    version = CovReporter.version_info_from_coverage_data(coverage)

                coverage = CovReporter.preprocess_coverage_data(coverage)

                if ret is None:
                    ret = coverage
                else:
                    CovReporter.__merge_coverage_data(ret, coverage)

        return (ret, version)

    @staticmethod
    def __merge_coverage_data(r, s):
        def merge_recursive(r, s):
            # These globals are mainly for debugging purposes. We count the number
            # of warnings we encounter during merging, which are mostly due to
            # bugs in GCOV. These statistics can be included in the report description
            # to track the status of these bugs.
            global null_coverable_count
            global length_mismatch_count
            global coverable_mismatch_count

            assert(r['name'] == s['name'])

            if "children" in s:
                for child in s['children']:
                    if child in r['children']:
                        # Slow path, child is in both data blobs,
                        # perform recursive merge.
                        merge_recursive(r['children'][child], s['children'][child])
                    else:
                        # Fast path, subtree only in merge source
                        r['children'][child] = s['children'][child]
            else:
                rc = r['coverage']
                sc = s['coverage']

                # GCOV bug, if the file has 0% coverage, then all of the file
                # is reported as not coverable. If s has that property, we simply
                # ignore it. If r has that property, we replace it by s.
                if sc.count(-1) == len(sc):
                    if rc.count(-1) != len(rc):
                        print("Warning: File %s reports no coverable lines" % r['name'])
                        null_coverable_count += 1
                    return

                if rc.count(-1) == len(rc):
                    if sc.count(-1) != len(sc):
                        print("Warning: File %s reports no coverable lines" % r['name'])
                        null_coverable_count += 1

                    r['coverage'] = sc
                    return

                # GCOV has mismatches on headers sometimes, ignore these, we
                # cannot fix this in any reasonable way.
                if len(rc) != len(sc):
                    print("Warning: Length mismatch for file %s (%s vs. %s)" % (r['name'], len(rc), len(sc)))
                    length_mismatch_count += 1
                    return

                # Disable the assertion for now
                #assert(len(r['coverage']) == len(s['coverage']))

                for idx in range(0, len(rc)):
                    if sc[idx] < 0:
                        # Verify that coverable vs. not coverable matches
                        # Unfortunately, GCOV again messes this up for headers sometimes
                        if rc[idx] >= 0:
                            print("Warning: Coverable/Non-Coverable mismatch for file %s (idx %s, %s vs. %s)" %
                                  (r['name'], idx, rc[idx], sc[idx]))
                            coverable_mismatch_count += 1

                        # Disable the assertion for now
                        #assert(r['coverage'][idx] < 0)
                    elif rc[idx] < 0 and sc[idx] >= 0:
                        rc[idx] = sc[idx]
                    else:
                        rc[idx] += sc[idx]

        # Merge recursively
        merge_recursive(r, s)

        # Recursively re-calculate all summary fields
        CovReporter.__calculate_summary_fields(r)

    @staticmethod
    def __calculate_summary_fields(node, name=None):
        node["name"] = name
        node["linesTotal"] = 0
        node["linesCovered"] = 0

        if "children" in node:
            # This node has subtrees, recurse on them
            for child_name in node["children"]:
                child = node["children"][child_name]
                CovReporter.__calculate_summary_fields(child, child_name)
                node["linesTotal"] += child["linesTotal"]
                node["linesCovered"] += child["linesCovered"]
        else:
            # This is a leaf, calculate linesTotal and linesCovered from
            # actual coverage data.
            coverage = node["coverage"]

            for line in coverage:
                if line >= 0:
                    node["linesTotal"] += 1
                    if line > 0:
                        node["linesCovered"] += 1

        # Calculate two more values based on total/covered because we need
        # them in the UI later anyway and can save some time by doing it here.
        node["linesMissed"] = node["linesTotal"] - node["linesCovered"]

        if node["linesTotal"] > 0:
            node["coveragePercent"] = round(((float(node["linesCovered"]) / node["linesTotal"]) * 100), 2)
        else:
            node["coveragePercent"] = 0.0


def main(argv=None):
    '''Command line options.'''

    # setup argparser
    parser = argparse.ArgumentParser()

    parser.add_argument('--version', action='version', version='%s v%s (%s)' %
                        (os.path.basename(__file__), __version__, __updated__))

    # Actions
    action_group = parser.add_argument_group("Actions", "A single action must be selected.")
    actions = action_group.add_mutually_exclusive_group(required=True)
    actions.add_argument("--submit", help="Submit the given file as coverage data", metavar="FILE")
    actions.add_argument("--multi-submit", action="store_true",
                         help="Submit multiple files (specified last on the command line)")

    # Generic Settings
    parser.add_argument("--serverhost", help="Server hostname for remote signature management", metavar="HOST")
    parser.add_argument("--serverport", type=int, help="Server port to use", metavar="PORT")
    parser.add_argument("--serverproto", help="Server protocol to use (default is https)", metavar="PROTO")
    parser.add_argument("--serverauthtokenfile", help="File containing the server authentication token", metavar="FILE")
    parser.add_argument("--clientid", help="Client ID to use when submitting coverage data", metavar="ID")
    parser.add_argument("--tool", help="Name of the tool that generated this coverage", metavar="NAME")

    # Coverage specific settings
    parser.add_argument("--repository", help="Name of the repository this coverage was measured on", metavar="NAME")
    parser.add_argument("--description", default="", help="Description for this coverage collection", metavar="NAME")

    parser.add_argument('rargs', nargs=argparse.REMAINDER)

    # process options
    opts = parser.parse_args(argv)

    serverauthtoken = None
    if opts.serverauthtokenfile:
        with open(opts.serverauthtokenfile) as f:
            serverauthtoken = f.read().rstrip()

    reporter = CovReporter(opts.serverhost, opts.serverport, opts.serverproto, serverauthtoken, opts.clientid,
                           opts.tool, opts.repository)

    if opts.submit or opts.multi_submit:
        if not opts.repository:
            print("Error: Must specify --repository when submitting coverage", file=sys.stderr)
            return 2

        if opts.submit:
            with open(opts.submit) as f:
                coverage = json.load(f)
            reporter.submit(coverage, description=opts.description)
        else:
            if not opts.rargs:
                print("Error: Must specify at least one file with --multi-submit", file=sys.stderr)
                return 2

            (coverage, version) = CovReporter.create_combined_coverage(opts.rargs)
            reporter.submit(coverage, preprocessed=True, version=version, description=opts.description)

    return 0


if __name__ == "__main__":
    sys.exit(main())
