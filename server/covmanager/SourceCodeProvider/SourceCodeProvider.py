'''
Source Code Provider Interface

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''

# Ensure print() compatibility with Python 3
from __future__ import print_function

from abc import ABCMeta, abstractmethod

class UnknownRevisionException(Exception):
    pass

class UnknownFilenameException(Exception):
    pass

class SourceCodeProvider():
    '''
    Abstract base class that defines what interfaces Source Code Providers must implement
    '''
    __metaclass__ = ABCMeta

    def __init__(self, location):
        self.location = location

    @abstractmethod
    def getSource(self, filename, revision):
        """
        Return the source code for the given filename on the given revision.

        @ptype filename: string
        @param filename: The path to the requested file, relative to the
                         root of the repository.

        @ptype revision: string
        @param revision: The revision to use when retrieving the source code.

        @rtype string
        @return The requested source code as a single string.
        """
        return

    @abstractmethod
    def testRevision(self, revision):
        """
        Check if the given revision exists in the resource associated with this provider.

        @ptype revision: string
        @param revision: The revision to check for.

        @rtype bool
        @return True, if the revision exists, False otherwise.
        """
        return

    @abstractmethod
    def update(self):
        """
        Update the resource associated with this provider.
        
        If the resource is e.g. a local repository, this would mean pulling
        new revisions from an associated repository (git fetch, hg pull, ..).
        
        Since calling this method is potentially expensive, it should only be
        called, when a revision has been determined to be not locally available
        (e.g. through the L{SourceCodeProvider.testRevision} method).
        """
        return
