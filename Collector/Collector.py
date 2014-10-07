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

# Ensure print() compatibility with Python 3
from __future__ import print_function

import sys
import os

from argparse import ArgumentParser
from FTB.Signatures.CrashSignature import CrashSignature
import hashlib
from FTB.Signatures.CrashInfo import CrashInfo

__all__ = []
__version__ = 0.1
__date__ = '2014-10-01'
__updated__ = '2014-10-01'

class Collector():
    def __init__(self, sigCacheDir, serverHost=None, serverPort=8080):
        '''
        @type sigCacheDir: string
        @param sigCacheDir: Directory to be used for caching signatures
        @type serverHost: string
        @param serverHost: Server host to contact for refreshing signatures
        @type serverPort: int
        @param serverPort: Server port to use when contacting server
        '''
        self.sigCacheDir = sigCacheDir
        self.serverHost = serverHost
        self.serverPort = serverPort
    
    
    def refresh(self):
        '''
        Refresh signatures by contacting the server, downloading new signatures
        and invalidating old ones.
        '''
        pass #TODO: Define JSON interface on server and call it here
    
    def submit(self, crashInfo, testCase=None, metaData=None):
        '''
        Refresh signatures by contacting the server, downloading new signatures
        and invalidating old ones.
        
        @type crashInfo: CrashInfo
        @param crashInfo: CrashInfo instance obtained from L{CrashInfo.fromRawCrashData}
        
        @type testCase: string
        @param testCase: A file containing a testcase for reproduction
        
        @type metaData: map
        @param metaData: A map containing arbitrary (application-specific) data which
                         will be stored on the server in JSON format.
        '''
        pass #TODO: Define JSON interface on server and call it here
    
    
    def search(self, crashInfo):
        '''
        Searches within the local signature cache directory for a signature matching the
        given crash. 
        
        @type crashInfo: CrashInfo
        @param crashInfo: CrashInfo instance obtained from L{CrashInfo.fromRawCrashData}
        
        @rtype: string
        @return: Filename of the signature file matching, or None if no match.
        '''
                
        cachedSigFiles = os.listdir(self.sigCacheDir)
        
        for sigFile in cachedSigFiles:
            with open(sigFile) as f:
                sigData = f.read()
                crashSig = CrashSignature(sigData)
                if crashSig.matches(crashInfo):
                    return sigFile
        
        return None
    
    def generate(self, crashInfo, forceCrashAddress=None, forceCrashInstruction=None, numFrames=None):
        '''
        Generates a signature in the local cache directory. It will be deleted when L{refresh} is called
        on the same local cache directory.
        
        @type crashInfo: CrashInfo
        @param crashInfo: CrashInfo instance obtained from L{CrashInfo.fromRawCrashData}
        
        @type forceCrashAddress: bool
        @param forceCrashAddress: Force including the crash address into the signature
        @type forceCrashInstruction: bool
        @param forceCrashInstruction: Force including the crash instruction into the signature (GDB only)
        @type numFrames: int
        @param numFrames: How many frames to include in the signature
        
        @rtype: string
        @return: File containing crash signature in JSON format
        '''
        
        sig = crashInfo.createCrashSignature(forceCrashAddress, forceCrashInstruction, numFrames)
        
        # Write the file to a unique file name
        h = hashlib.new('sha1')
        h.update(sig)
        with open(os.path.join(self.sigCacheDir, h.hexdigest() + ".signature"), 'w') as f:
            f.write(sig) 
        

def main(argv=None):
    '''Command line options.'''

    program_name = os.path.basename(sys.argv[0])
    program_version = "v%s" % __version__
    program_build_date = "%s" % __updated__

    program_version_string = '%%prog %s (%s)' % (program_version, program_build_date)

    if argv is None:
        argv = sys.argv[1:]

    # setup argparser
    parser = ArgumentParser()
    parser.add_argument('--version', action='version', version=program_version_string)
    
    # Crash information
    parser.add_argument("--stdout", dest="stdout", help="File containing STDOUT data", metavar="FILE")
    parser.add_argument("--stderr", dest="stderr", help="File containing STDERR data", metavar="FILE")
    parser.add_argument("--crashdata", dest="crashdata", help="File containing external crash data", metavar="FILE")

    # Actions
    parser.add_argument("--refresh", dest="refresh", action='store_true', help="Perform a signature refresh")
    parser.add_argument("--search", dest="search", action='store_true', help="Search cached signatures for the given crash")
    parser.add_argument("--generate", dest="generate", help="Create a (temporary) local signature in the cache directory")

    # Settings
    parser.add_argument("--sigdir", dest="sigdir", help="Signature cache directory", metavar="DIR")
    parser.add_argument("--serverhost", dest="serverhost", help="Server hostname for remote signature management", metavar="HOST")
    parser.add_argument("--serverport", dest="serverport", type=int, help="Server port to use", metavar="PORT")
    parser.add_argument("--platform", dest="platform", help="Restrict matching to the specified platform", metavar="(x86|x86-64|arm)")
    parser.add_argument("--product", dest="product", help="Restrict matching to the specified product", metavar="PRODUCT")
    parser.add_argument("--os", dest="os", help="Restrict matching to the specified OS", metavar="(windows|linux|macosx|b2g|android)")
    
    parser.add_argument("--forcecrashaddr", dest="forcecrashaddr", action='store_true', help="Force including the crash address into the signature")
    parser.add_argument("--forcecrashinst", dest="forcecrashinst", action='store_true', help="Force including the crash instruction into the signature (GDB only)")
    parser.add_argument("--numframes", dest="numframes", type=int, help="How many frames to include into the signature (default is 8)")

    if len(argv) == 0:
        parser.print_help()
        return 2

    # process options
    (opts, args) = parser.parse_args(argv)
    
    if opts.search and opts.create:
        print("Error: Can't --search and --generate at the same time", file=sys.stderr)

    stdout = None
    stderr = None
    crashdata = None
    crashInfo = None

    if opts.search or opts.create:
        if opts.stderr == None and opts.crashdata == None:
            print("Error: Must specify at least either --stderr or --crashdata file", file=sys.stderr)
        
        if stdout:
            with open(stdout) as f:
                stdout = f.readLines()
        
        if stderr:
            with open(stderr) as f:
                stderr = f.readLines()
            
        if crashdata:
            with open(crashdata) as f:
                crashdata = f.readLines()
                
        crashInfo = CrashInfo.fromRawCrashData(stdout, stderr, crashdata, opts.platform, opts.product, opts.os)

            
    collector = Collector(opts.sigdir, opts.serverhost, opts.serverport)
    
    if opts.refresh:
        collector.refresh()
    
    if opts.search:
        sig = collector.search(crashInfo)
        if sig == None:
            print("No match found")
            return 1
        print(sig)
        return 0
    
    if opts.generate:
        sigFile = collector.generate(crashInfo, opts.forcecrashaddr, opts.forcecrashinst, opts.numframes)
        print(sigFile)



if __name__ == "__main__":
    sys.exit(main())