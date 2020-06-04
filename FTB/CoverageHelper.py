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

import re


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
                    #print("Warning: File %s reports no coverable lines" % r['name'])
                    stats['null_coverable_count'] += 1
                return

            if rc.count(-1) == len(rc):
                if sc.count(-1) != len(sc):
                    #print("Warning: File %s reports no coverable lines" % r['name'])
                    stats['null_coverable_count'] += 1

                r['coverage'] = sc
                return

            # grcov does not always output the correct length for files when they end in non-coverable lines.
            # We record this, then ignore the excess lines.
            if len(rc) != len(sc):
                #print("Warning: Length mismatch for file %s (%s vs. %s)" % (r['name'], len(rc), len(sc)))
                stats['length_mismatch_count'] += 1

            # Disable the assertion for now
            #assert(len(r['coverage']) == len(s['coverage']))

            minlen = min(len(rc), len(sc))

            for idx in range(0, minlen):
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
                    #print("Warning: Coverable/Non-Coverable mismatch for file %s (idx %s, %s vs. %s)" %
                    #      (r['name'], idx, rc[idx], sc[idx]))
                    stats['coverable_mismatch_count'] += 1

                    # Explicitly mark as not coverable
                    rc[idx] = -1
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


def apply_include_exclude_directives(node, directives):
    """
    Applies the given include and exclude directives to the given nodeself.
    Directives either start with a + or a - for include or exclude, followed
    by a colon and a glob expression. The glob expression must match the
    full path of the file(s) or dir(s) to include or exclude. All slashes in paths
    are forward slashes, must not have a trailing slash and glob characters
    are not allowed. ** is additionally supported for recursive directory matching.
    @param node: The coverage node to modify, in server-side recursive format
    @type node: dict
    @param directives: The directives to apply
    @type directives: list(str)
    This method modifies the node in-place, nothing is returned.
    IMPORTANT: This method does *not* recalculate any total/summary fields.
               You *must* call L{calculate_summary_fields} after applying
               this function one or more times to ensure correct results.
    """

    # Pre-process the directives
    #
    # all directives become a tuple of their "/" separated parts
    #
    # there are only two base-cases:
    #  <directive> ::= "**"
    #                | pattern
    #                | <directive> "/" <directive>
    #
    # ** are left as a string
    # patterns are converted to regex and compile
    directives_new = [("+", ["**"])]  # start with an implicit +:** so we don't have to handle the empty case
    for directive in directives:
        directive = directive.lstrip()
        if directive.startswith("#") or not len(directive):
            # Ignore empty lines and Python style comments
            continue

        if ":" not in directive:
            raise RuntimeError("malformed directive: " + repr(directive))
        what, pattern = directive.split(":", 1)
        if what not in "+-":
            raise RuntimeError("Unexpected directive prefix: " + what)
        parts = []
        for part in pattern.split("/"):
            if part == "**":
                parts.append(part)
            elif "**" in part:
                # although this is technically still a valid glob, raise an error since ** has special meaning
                # and this probably indicates a misunderstanding of what it will do
                # (functionally, ** == * if it was left in)
                raise RuntimeError("** cannot be used in an expression")
            else:
                # escape regex characters
                part = re.escape(part) + "$"  # add $ so whole pattern must match
                # convert glob pattern to regex
                part = part.replace("\\*", ".*").replace("\\?", ".")
                # compile the resulting regex
                parts.append(re.compile(part))
        directives_new.append((what, parts))

    def _is_dir(node):
        return "children" in node

    def __apply_include_exclude_directives(node, directives):
        if not _is_dir(node):
            return

        #print("\tdirectives = [ " +
        #      ", ".join(w + ":" + "/".join("**" if d == "**" else d.pattern for d in p) for (w, p) in directives) +
        #      "]")

        # separate out files from dirs
        original_files = []
        original_dirs = []
        for child in node["children"]:
            if _is_dir(node["children"][child]):
                original_dirs.append(child)
            else:
                original_files.append(child)

        # run directives on files
        files = set()
        for what, parts in directives:
            pattern, subtree_pattern = parts[0], parts[1:]

            # there is still a "/" in the pattern, so it shouldn't be applied to files at this point
            if subtree_pattern:
                continue

            if what == "+":
                if pattern == "**":
                    files = set(original_files)
                else:
                    files |= {child for child in original_files if pattern.match(child) is not None}
            else:  # what == "-"
                if pattern == "**":
                    files = set()
                else:
                    files = {child for child in files if pattern.match(child) is None}

        # run directives on dirs
        universal_directives = []  # patterns beginning with **/ should always be applied recursively
        dirs = {}
        for what, parts in directives:
            pattern, subtree_pattern = parts[0], parts[1:]

            if pattern == "**":
                # ** is unique in that it applies to both files and directories at every level
                # it is also the only pattern that can remove a directory from recursion
                if subtree_pattern:
                    universal_directives.append((what, parts))
                else:
                    # +:** or -:** means it doesn't matter what preceded this,
                    #   so ignore the existing universal_directives
                    universal_directives = [(what, parts)]

                    # this is a unique case, so handle it separately
                    # it will either reset dirs to all directory children of the current node, or clear dirs
                    if what == "+":
                        dirs = {child: [(what, parts)] for child in original_dirs}
                    else:  # what == "-"
                        dirs = {}
                    continue

            # ** is the only case we care about that is not a subtree pattern, and it was already handled above
            if not subtree_pattern:
                continue

            if what == "+":
                for child in original_dirs:
                    if pattern == "**" or pattern.match(child) is not None:
                        if child not in dirs:
                            dirs[child] = universal_directives[:]
                        elif pattern == "**":
                            dirs[child].append((what, parts))
                        dirs[child].append((what, subtree_pattern))
            else:  # what == "-"
                for child in dirs:
                    if pattern == "**":
                        dirs[child].append((what, parts))
                    if pattern == "**" or pattern.match(child) is not None:
                        dirs[child].append((what, subtree_pattern))

            if pattern == "**":
                universal_directives.append((what, subtree_pattern))

        # filters are applied, now remove/recurse for each child
        for child in list(node["children"]):  # make a copy since elements will be removed during iteration
            if _is_dir(node["children"][child]):
                if child in dirs:
                    #print("recursing to %s/%s" % (node["name"], node["children"][child]["name"]))
                    __apply_include_exclude_directives(node["children"][child], dirs[child])
                    # the child is now empty, so remove it too
                    if not node["children"][child]["children"]:
                        del node["children"][child]
                else:
                    del node["children"][child]  # removing excluded subtree
            elif child not in files:
                del node["children"][child]  # removing excluded file

    # begin recursion
    __apply_include_exclude_directives(node, directives_new)


def get_flattened_names(node, prefix=""):
    """
    Returns a list of flattened paths (files and directories) of the given node.

    Paths will include the leading slash if the node a top-level node.
    All slashes in paths will be forward slashes and not use any trailing slashes.

    @param node: The coverage node to process, in server-side recursive format
    @type node: dict

    @param prefix: An optional prefix to prepend to each name
    @type prefix: str

    @return The list of all paths occurring in the given node.
    @rtype: list(str)
    """
    def __get_flattened_names(node, prefix, result):
        current_name = node["name"]
        if current_name is None:
            new_prefix = ""
        else:
            if prefix:
                new_prefix = "%s/%s" % (prefix, current_name)
            else:
                new_prefix = current_name
            result.add(new_prefix)

        if "children" in node:
            for child_name in node["children"]:
                child = node["children"][child_name]
                __get_flattened_names(child, new_prefix, result)
        return result

    return __get_flattened_names(node, prefix, set())
