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
import json
import base64

BASE_DIR = os.path.dirname(os.path.realpath(__file__))
FTB_PATH = os.path.abspath(os.path.join(BASE_DIR, ".."))
sys.path += [FTB_PATH]

from argparse import ArgumentParser
from FTB.Signatures.CrashSignature import CrashSignature
import hashlib
from FTB.Signatures.CrashInfo import CrashInfo
import requests
from FTB.ProgramConfiguration import ProgramConfiguration

__all__ = []
__version__ = 0.1
__date__ = '2014-10-01'
__updated__ = '2014-10-01'

class Collector():
    def __init__(self, sigCacheDir, serverHost=None, serverPort=8080,
                 serverProtocol="https", serverUser=None, serverPass=None,
                 clientId=None):
        '''
        @type sigCacheDir: string
        @param sigCacheDir: Directory to be used for caching signatures
        @type serverHost: string
        @param serverHost: Server host to contact for refreshing signatures
        @type serverPort: int
        @param serverPort: Server port to use when contacting server
        @type serverUser: string
        @param serverUser: Username for server authentication
        @type serverPass: string
        @param serverPass: Password for server authentication
        @type clientId: string
        @param clientId: Client ID stored in the server when submitting issues
        '''
        self.sigCacheDir = sigCacheDir
        self.serverHost = serverHost
        self.serverPort = serverPort
        self.serverProtocol = serverProtocol
        self.serverCreds = (serverUser, serverPass)
        self.clientId = clientId
        
        if self.serverHost != None and self.clientId == None:
            raise RuntimeError("Must specify clientId when instantiating with server parameters")
    
    def refresh(self):
        '''
        Refresh signatures by contacting the server, downloading new signatures
        and invalidating old ones.
        '''     
        if not self.serverHost:
            raise RuntimeError("Must specify serverHost to use remote features.")
        
        url = "%s://%s:%s/crashmanager/rest/signatures/" % (self.serverProtocol, self.serverHost, self.serverPort)
        
        response = requests.get(url, auth=self.serverCreds)
        
        if response.status_code != requests.codes["ok"]:
            raise RuntimeError("Server unexpectedly responded with status code %s" % response.status_code)
        
        json = response.json()
        
        if not isinstance(json, list):
            raise RuntimeError("Server sent malformed JSON response: %s" % json)
        
        for sigFile in os.listdir(self.sigCacheDir):
            if sigFile.endswith(".signature"):
                os.remove(os.path.join(self.sigCacheDir, sigFile))
            else:
                print("Warning: Skipping deletion of non-signature file: %s" % sigFile, file=sys.stderr)
        
        for rawBucketObj in json:
            try:
                self.__store_signature_hashed(CrashSignature(rawBucketObj["signature"]))
            except RuntimeError, e:
                print("Warning: Received broken signature (%s): %s" % (e, rawBucketObj["signature"]), file=sys.stderr)
    
    def submit(self, crashInfo, testCase=None, testCaseQuality=0, metaData=None):
        '''
        Submit the given crash information and an optional testcase/metadata
        to the server for processing and storage.
        
        @type crashInfo: CrashInfo
        @param crashInfo: CrashInfo instance obtained from L{CrashInfo.fromRawCrashData}
        
        @type testCase: string
        @param testCase: A file containing a testcase for reproduction
        
        @type testCaseQuality: int
        @param testCaseQuality: A value indicating the quality of the test (less is better)
        
        @type metaData: map
        @param metaData: A map containing arbitrary (application-specific) data which
                         will be stored on the server in JSON format.
        '''
        if not self.serverHost:
            raise RuntimeError("Must specify serverHost to use remote features.")
        
        url = "%s://%s:%s/crashmanager/rest/crashes/" % (self.serverProtocol, self.serverHost, self.serverPort)
        
        # Serialize our crash information, testcase and metadata into a dictionary to POST
        data = {}
        
        data["rawStdout"] = os.linesep.join(crashInfo.rawStdout)
        data["rawStderr"] = os.linesep.join(crashInfo.rawStderr)
        data["rawCrashData"] = os.linesep.join(crashInfo.rawCrashData)
        
        if testCase:
            with open(testCase) as f:
                testCaseData = f.read()
            
            textBytes = bytearray([7,8,9,10,12,13,27]) + bytearray(range(0x20, 0x100))
            isBinary = lambda input: bool(input.translate(None, textBytes))
            if isBinary(testCaseData): 
                testCaseData = base64.b64encode(testCaseData)
                data["testcase_isbinary"] = True
            else:
                data["testcase_isbinary"] = False

            data["testcase"] = testCaseData
            data["testcase_quality"] = testCaseQuality
            data["testcase_ext"] = os.path.splitext(testCase)[1][1:]
            
        data["platform"] = crashInfo.configuration.platform
        data["product"] = crashInfo.configuration.product
        data["os"] = crashInfo.configuration.os
        
        if crashInfo.configuration.version:
            data["product_version"] = crashInfo.configuration.version
        
        data["client"] = self.clientId
        
        if metaData:
            data["metadata"] = json.dumps(metaData)
        
        if crashInfo.configuration.env:
            data["env"] = json.dumps(crashInfo.configuration.env)
        
        if crashInfo.configuration.args:
            data["args"] = json.dumps(crashInfo.configuration.args)
        
        response = requests.post(url, data, auth=self.serverCreds)
        
        if response.status_code != requests.codes["created"]:
            raise RuntimeError("Server unexpectedly responded with status code %s" % response.status_code)

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
            sigFile = os.path.join(self.sigCacheDir, sigFile)
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
        return self.__store_signature_hashed(sig)
            
    def __store_signature_hashed(self, signature):
        '''
        Store a signature, using the sha1 hash hex representation as filename.
        
        @type signature: CrashSignature
        @param signature: CrashSignature to store
        
        @rtype: string
        @return: Name of the file that the signature was written to
        
        '''
        h = hashlib.new('sha1')
        h.update(str(signature))
        sigfile = os.path.join(self.sigCacheDir, h.hexdigest() + ".signature")
        with open(sigfile, 'w') as f:
            f.write(str(signature))
            
        return sigfile

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
    parser.add_argument("--submit", dest="submit", action='store_true', help="Submit a signature to the server")
    parser.add_argument("--search", dest="search", action='store_true', help="Search cached signatures for the given crash")
    parser.add_argument("--generate", dest="generate", action='store_true', help="Create a (temporary) local signature in the cache directory")

    # Settings
    parser.add_argument("--sigdir", dest="sigdir", help="Signature cache directory", metavar="DIR")
    parser.add_argument("--serverhost", dest="serverhost", help="Server hostname for remote signature management", metavar="HOST")
    parser.add_argument("--serverport", dest="serverport", type=int, help="Server port to use", metavar="PORT")
    parser.add_argument("--serverproto", dest="serverproto", default="https", help="Server protocol to use (default is https)", metavar="PROTO")
    parser.add_argument("--servercreds", dest="servercreds", help="Credentials file (contains username and password on separate lines)", metavar="FILE")
    parser.add_argument("--clientid", dest="clientid", help="Client ID to use when submitting issues", metavar="ID")
    parser.add_argument("--platform", dest="platform", help="Platform this crash appeared on", metavar="(x86|x86-64|arm)")
    parser.add_argument("--product", dest="product", help="Product this crash appeared on", metavar="PRODUCT")
    parser.add_argument("--productversion", dest="product_version", help="Product version this crash appeared on", metavar="VERSION")
    parser.add_argument("--os", dest="os", help="OS this crash appeared on", metavar="(windows|linux|macosx|b2g|android)")
    parser.add_argument('--args', dest='args', nargs='+', type=str, help="List of program arguments. Backslashes can be used for escaping and are stripped.")
    parser.add_argument('--env', dest='env', nargs='+', type=str, help="List of environment variables in the form 'KEY=VALUE'")
    parser.add_argument('--metadata', dest='metadata', nargs='+', type=str, help="List of metadata variables in the form 'KEY=VALUE'")

    parser.add_argument("--testcase", dest="testcase", help="File containing testcase", metavar="FILE")
    parser.add_argument("--testcasequality", dest="testcasequality", default="0", help="Integer indicating test case quality (0 is best and default)", metavar="VAL")

    # Options that affect how signatures are generated
    parser.add_argument("--forcecrashaddr", dest="forcecrashaddr", action='store_true', help="Force including the crash address into the signature")
    parser.add_argument("--forcecrashinst", dest="forcecrashinst", action='store_true', help="Force including the crash instruction into the signature (GDB only)")
    parser.add_argument("--numframes", dest="numframes", default=8, type=int, help="How many frames to include into the signature (default is 8)")



    if len(argv) == 0:
        parser.print_help()
        return 2

    # process options
    opts = parser.parse_args(argv)
    
    if opts.search and opts.generate:
        print("Error: Can't --search and --generate at the same time", file=sys.stderr)

    stdout = None
    stderr = None
    crashdata = None
    crashInfo = None
    args = None
    env = None
    metadata = None
    
    if opts.search or opts.generate or opts.refresh:
        if opts.sigdir == None:
            print("Error: Must specify --sigdir", file=sys.stderr)
            return 2
            


    if opts.search or opts.generate or opts.submit:
        if opts.platform == None or opts.product == None or opts.os == None:
            print("Error: Must specify at least --platform, --product and --os", file=sys.stderr)
            return 2
        
        if opts.stderr == None and opts.crashdata == None:
            print("Error: Must specify at least either --stderr or --crashdata file", file=sys.stderr)
            return 2
        
        if opts.stdout:
            with open(opts.stdout) as f:
                stdout = f.read()
        
        if opts.stderr:
            with open(opts.stderr) as f:
                stderr = f.read()
            
        if opts.crashdata:
            with open(opts.crashdata) as f:
                crashdata = f.read()
                
        if opts.args:
            args = [arg.replace('\\', '') for arg in opts.args]
            
        if opts.env:
            env = dict(kv.split('=', 1) for kv in opts.env)
        
        if opts.metadata:
            metadata = dict(kv.split('=', 1) for kv in opts.metadata)
                
        configuration = ProgramConfiguration(opts.product, opts.platform, opts.os, opts.product_version, env, args)
        crashInfo = CrashInfo.fromRawCrashData(stdout, stderr, configuration, auxCrashData=crashdata)

    serveruser = None
    serverpass = None
    
    if opts.servercreds:
        with open(opts.servercreds) as f:
            (serveruser, serverpass) = f.read().splitlines()
            
    collector = Collector(opts.sigdir, opts.serverhost, opts.serverport, opts.serverproto, serveruser, serverpass, opts.clientid)
    
    if opts.refresh or opts.submit:
        if not opts.serverhost:
            print("Error: Must specify --serverhost for remote features.", file=sys.stderr)
            return 2
    
    if opts.refresh:
        collector.refresh()
        
    if opts.submit:
        testcase = opts.testcase        
        collector.submit(crashInfo, testcase, opts.testcasequality, metadata)
    
    if opts.search:
        sig = collector.search(crashInfo)
        if sig == None:
            print("No match found")
            return 3
        print(sig)
        return 0
    
    if opts.generate:
        sigFile = collector.generate(crashInfo, opts.forcecrashaddr, opts.forcecrashinst, opts.numframes)
        print(sigFile)
        return 0



if __name__ == "__main__":
    sys.exit(main())