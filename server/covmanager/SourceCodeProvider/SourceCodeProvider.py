'''
Source Code Provider Interface

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''

from __future__ import annotations

from abc import ABCMeta, abstractmethod

import six
from typing_extensions import NotRequired
from typing_extensions import TypedDict


class UnknownRevisionException(Exception):
    pass


class UnknownFilenameException(Exception):
    pass


@six.add_metaclass(ABCMeta)
class SourceCodeProvider():
    '''
    Abstract base class that defines what interfaces Source Code Providers must implement
    '''
    def __init__(self, location: str) -> None:
        self.location = location

    @abstractmethod
    def getSource(self, filename: str, revision: str) -> str:
        """
        Return the source code for the given filename on the given revision.

        @param filename: The path to the requested file, relative to the
                         root of the repository.
        @param revision: The revision to use when retrieving the source code.
        @return The requested source code as a single string.
        """
        return ""

    @abstractmethod
    def testRevision(self, revision: str) -> bool:
        """
        Check if the given revision exists in the resource associated with this provider.

        @param revision: The revision to check for.
        @return True, if the revision exists, False otherwise.
        """
        return False

    @abstractmethod
    def update(self) -> None:
        """
        Update the resource associated with this provider.

        If the resource is e.g. a local repository, this would mean pulling
        new revisions from an associated repository (git fetch, hg pull, ..).

        Since calling this method is potentially expensive, it should only be
        called, when a revision has been determined to be not locally available
        (e.g. through the L{SourceCodeProvider.testRevision} method).
        """
        return

    @abstractmethod
    def getParents(self, revision: str) -> list[str]:
        """
        Gets the parent revisions of the specified revision.

        @param revision: The revision to get parents for.
        @return The list of parent revisions.
        """
        return []

    @abstractmethod
    def getUnifiedDiff(self, revision: str) -> str:
        """
        Return a GIT-style unified diff for the given revision.

        @param revision: The revision to get the diff for.
        @return The unified diff as a single string.
        """
        return ""

    @abstractmethod
    def checkRevisionsEquivalent(self, revisionA: str, revisionB: str) -> bool:
        """
        Check if the given revisions are considered to be equivalent.

        @param revisionA: The first revision to compare.
        @param revisionB: The second revision to compare.
        @return True, if the revisions are equivalent, False otherwise.
        """
        return False


class CObj(TypedDict):
    """CObj type specification."""

    filename: str | None
    locations: list[int]
    missed: NotRequired[list[int]]
    not_coverable: NotRequired[list[int]]


class Utils():

    @staticmethod
    def getDiffLocations(diff: str) -> list[CObj]:
        """
        This method tries to return reasonable diff hunk locations for each
        changed file in the given unified diff, where the locations refer to the
        version before the patch is applied. We define the location of a diff
        hunk as follows:

        - If the diff hunk adds and removes lines, then the location of the diff
          hunk is the set of lines which were removed.

        - If the diff hunk only adds lines, then we should consider the lines
          surrounding the added hunk as the location of the diff hunk.

        These definitions aim at trying to return locations that point to the
        faulty code, which can again be used for coverage analysis.

        Note that the heuristics used here are far from perfect and are only
        meant to aid manual inspection.

        @param diff: A GIT-style unified diff as a single string.
        @return A list containing one object per file changed. Each object in
                the list has two attributes, "filename" and "locations", where
                "locations" is the list of diff hunk locations for that
                particular file.
        """
        ret: list[CObj] = []
        diff_list = diff.splitlines()

        while diff_list:
            cobj: CObj = {"filename": None, "locations": []}

            skipDiff = False

            line = diff_list.pop(0)

            if line.startswith("diff --git "):
                (mm, mmLine) = diff_list.pop(0).split(" ", 2)
                (pp, ppLine) = diff_list.pop(0).split(" ", 2)

                if not mm == "---" or not pp == "+++":
                    raise RuntimeError("Malformed trace")

                if mmLine[2:] != ppLine[2:]:
                    skipDiff = True

                cobj["filename"] = mmLine[2:]

            skipHunk = False
            lastHunkStart = 0
            hunkLineRemoveCount = 0

            while diff_list and not diff_list[0].startswith("diff --git "):
                line = diff_list.pop(0)

                if not skipDiff:
                    if line.startswith("@@ "):
                        lastHunkStart = abs(int(line.split(" ")[1].split(",")[0]))
                        skipHunk = False
                        hunkLineRemoveCount = 0
                    elif skipHunk:
                        continue
                    elif line.startswith("-"):
                        cobj["locations"].append(lastHunkStart + hunkLineRemoveCount)
                        hunkLineRemoveCount += 1
                    elif line.startswith("+"):
                        if not hunkLineRemoveCount:
                            cobj["locations"].append(lastHunkStart)
                            cobj["locations"].append(lastHunkStart + 1)
                        skipHunk = True

            if not skipDiff:
                ret.append(cobj)
        return ret
