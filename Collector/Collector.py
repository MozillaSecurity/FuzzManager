#!/usr/bin/env python
# encoding: utf-8
'''
Collector -- Crash processing client

Provide process and class level interfaces to process crash information with
a remote server.

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''

import sys
import os

from optparse import OptionParser
from FTB.Signatures import CrashSignature
from FTB.Signatures.CrashInfo import CrashInfo

__all__ = []
__version__ = 0.1
__date__ = '2014-10-01'
__updated__ = '2014-10-01'

class Collector():
    def __init__(self, sigCacheDir, serverHost=None, serverPort=8080):
        '''
        
        :param sigCacheDir: Directory to be used for caching signatures
        :param serverHost: Server host to contact for refreshing signatures
        :param serverPort: Server port to use when contacting server
        '''
        self.sigCacheDir = sigCacheDir
    
    
    def refresh(self):
        '''
        Refresh signatures by contacting the server, downloading new signatures
        and invalidating old ones.
        '''
        pass #TODO: Define JSON interface on server and call it here
    
    
    def search(self, stdout, stderr, crashData=None, platform=None, product=None, os=None):
        '''
        Searches within the local signature cache directory for a signature matching the
        given crash. 
        
        :param stdout: List of lines as they appeared on stdout
        :param stderr: List of lines as they appeared on stderr
        :param crashData: Optional crash output (e.g. GDB). If not specified, assumed to be on stderr.
        :param platform: Optional platform to match the signature platform attribute
        :param product: Optional product to match the signature product attribute
        :param os: Optional OS to match the signature OS attribute
        '''
        
        crashInfo = CrashInfo.fromRawCrashData(stdout, stderr, crashData, platform, product, os)
        
        cachedSigFiles = os.listdir(self.sigCacheDir)
        
        for sigFile in cachedSigFiles:
            crashSig = CrashSignature(sigFile)
            #TODO: Match crashsig here, return result
        
        

def main(argv=None):
    '''Command line options.'''

    program_name = os.path.basename(sys.argv[0])
    program_version = "v%s" % __version__
    program_build_date = "%s" % __updated__

    program_version_string = '%%prog %s (%s)' % (program_version, program_build_date)

    if argv is None:
        argv = sys.argv[1:]
    try:
        # setup option parser
        parser = OptionParser(version=program_version_string)
        
        #parser.add_option("-i", "--in", dest="infile", help="set input path [default: %default]", metavar="FILE")
        #parser.add_option("-o", "--out", dest="outfile", help="set output path [default: %default]", metavar="FILE")
        #parser.add_option("-v", "--verbose", dest="verbose", action="count", help="set verbosity level [default: %default]")

        # set defaults
        #parser.set_defaults(outfile="./out.txt", infile="./in.txt")

        # process options
        (opts, args) = parser.parse_args(argv)

        if opts.verbose > 0:
            print("verbosity level = %d" % opts.verbose)
        
        #TODO: Write main

    except Exception, e:
        indent = len(program_name) * " "
        sys.stderr.write(program_name + ": " + repr(e) + "\n")
        sys.stderr.write(indent + "  for help use --help")
        return 2


if __name__ == "__main__":
    sys.exit(main())