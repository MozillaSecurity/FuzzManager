#!/usr/bin/env python
# encoding: utf-8
'''
CoverageHelper -- Various methods around processing coverage data

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''

# Ensure print() compatibility with Python 3
from __future__ import print_function


def merge_coverage_data(r, s):
    # These variables are mainly for debugging purposes. We count the number
    # of warnings we encounter during merging, which are mostly due to
    # bugs in GCOV. These statistics can be included in the report description
    # to track the status of these bugs.
    stats = {
        'null_coverable_count': 0,
        'length_mismatch_count': 0,
        'coverable_mismatch_count': 0
    }

    def merge_recursive(r, s):
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
                    stats['null_coverable_count'] += 1
                return

            if rc.count(-1) == len(rc):
                if sc.count(-1) != len(sc):
                    print("Warning: File %s reports no coverable lines" % r['name'])
                    stats['null_coverable_count'] += 1

                r['coverage'] = sc
                return

            # GCOV has mismatches on headers sometimes, ignore these, we
            # cannot fix this in any reasonable way.
            if len(rc) != len(sc):
                print("Warning: Length mismatch for file %s (%s vs. %s)" % (r['name'], len(rc), len(sc)))
                stats['length_mismatch_count'] += 1
                return

            # Disable the assertion for now
            #assert(len(r['coverage']) == len(s['coverage']))

            for idx in range(0, len(rc)):
                # There are multiple situations where coverage reports might disagree
                # about which lines are coverable and which are not. Sometimes, GCOV
                # reports this wrong in headers, but it can also happen when mixing
                # Clang and GCOV reports. Clang seems to consider more lines as coverable
                # than GCOV.
                #
                # As a short-term solution we will always treat a location as *not* coverable
                # if any of the reports says it is not coverable. We will still record these
                # mismatches so we can track them and confirm them going down once we fix the
                # various root causes for this behavior.
                if (sc[idx] < 0 and rc[idx] >= 0) or (rc[idx] < 0 and sc[idx] >= 0):
                    print("Warning: Coverable/Non-Coverable mismatch for file %s (idx %s, %s vs. %s)" %
                          (r['name'], idx, rc[idx], sc[idx]))
                    stats['coverable_mismatch_count'] += 1

                if sc[idx] < 0 and rc[idx] >= 0:
                    rc[idx] = sc[idx]
                elif rc[idx] < 0 and sc[idx] >= 0:
                    pass
                elif rc[idx] >= 0 and sc[idx] >= 0:
                    rc[idx] += sc[idx]

    # Merge recursively
    merge_recursive(r, s)

    # Recursively re-calculate all summary fields
    calculate_summary_fields(r)

    return stats


def calculate_summary_fields(node, name=None):
    node["name"] = name
    node["linesTotal"] = 0
    node["linesCovered"] = 0

    if "children" in node:
        # This node has subtrees, recurse on them
        for child_name in node["children"]:
            child = node["children"][child_name]
            calculate_summary_fields(child, child_name)
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
