#!/usr/bin/env python3
"""
Collector -- Crash processing client

Provide process and class level interfaces to process crash information with
a remote server.

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
"""
import argparse
import base64
import hashlib
import json
import os
import shutil
import sys
from tempfile import mkstemp
from zipfile import ZipFile

from FTB.ProgramConfiguration import ProgramConfiguration
from FTB.Running.AutoRunner import AutoRunner
from FTB.Signatures.CrashInfo import CrashInfo
from FTB.Signatures.CrashSignature import CrashSignature
from Reporter.Reporter import Reporter, remote_checks, signature_checks

__all__ = []
__version__ = 0.1
__date__ = "2014-10-01"
__updated__ = "2014-10-01"


class KeyValueAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        result = {}
        for item in values:
            try:
                key, value = item.split("=", 1)
                result[key] = value
            except ValueError:
                raise argparse.ArgumentTypeError(
                    f"Invalid format: '{item}', expected key=value."
                )
        setattr(namespace, self.dest, result)


class Collector(Reporter):
    @remote_checks
    @signature_checks
    def refresh(self):
        """
        Refresh signatures by contacting the server, downloading new signatures
        and invalidating old ones.
        """
        url = "%s://%s:%d/crashmanager/rest/signatures/download/" % (
            self.serverProtocol,
            self.serverHost,
            self.serverPort,
        )

        response = self.get(url, stream=True)

        (zipFileFd, zipFileName) = mkstemp(prefix="fuzzmanager-signatures")

        with os.fdopen(zipFileFd, "wb") as zipFile:
            shutil.copyfileobj(response.raw, zipFile)

        self.refreshFromZip(zipFileName)
        os.remove(zipFileName)

    @signature_checks
    def refreshFromZip(self, zipFileName):
        """
        Refresh signatures from a local zip file, adding new signatures
        and invalidating old ones. (This is a non-standard use case;
        you probably want to use refresh() instead.)
        """
        with ZipFile(zipFileName, "r") as zipFile:
            if zipFile.testzip():
                raise RuntimeError(f"Bad CRC for downloaded zipfile {zipFileName}")

            # Now clean the signature directory, only deleting signatures and metadata
            for sigFile in os.listdir(self.sigCacheDir):
                if sigFile.endswith(".signature") or sigFile.endswith(".metadata"):
                    os.remove(os.path.join(self.sigCacheDir, sigFile))
                else:
                    print(
                        "Warning: Skipping deletion of non-signature file:",
                        sigFile,
                        file=sys.stderr,
                    )

            zipFile.extractall(self.sigCacheDir)

    @remote_checks
    def submit(
        self,
        crashInfo,
        testCase=None,
        testCaseQuality=0,
        testCaseSize=None,
        metaData=None,
    ):
        """
        Submit the given crash information and an optional testcase/metadata
        to the server for processing and storage.

        @type crashInfo: CrashInfo
        @param crashInfo: CrashInfo instance obtained from L{CrashInfo.fromRawCrashData}

        @type testCase: string
        @param testCase: A file containing a testcase for reproduction

        @type testCaseQuality: int
        @param testCaseQuality: A value indicating the quality of the test (less is
                                better)

        @type testCaseSize: int or None
        @param testCaseSize: The size of the testcase to report. If None, use the file
                             size.

        @type metaData: map
        @param metaData: A map containing arbitrary (application-specific) data which
                         will be stored on the server in JSON format. This metadata is
                         combined with possible metadata stored in the
                         L{ProgramConfiguration} inside crashInfo.
        """
        url = "%s://%s:%d/crashmanager/rest/crashes/" % (
            self.serverProtocol,
            self.serverHost,
            self.serverPort,
        )

        # Serialize our crash information, testcase and metadata into a dictionary to
        # POST
        data = {}

        data["rawStdout"] = os.linesep.join(crashInfo.rawStdout)
        data["rawStderr"] = os.linesep.join(crashInfo.rawStderr)
        data["rawCrashData"] = os.linesep.join(crashInfo.rawCrashData)

        if testCase:
            (testCaseData, isBinary) = Collector.read_testcase(testCase)

            if testCaseSize is None:
                testCaseSize = len(testCaseData)

            if isBinary:
                testCaseData = base64.b64encode(testCaseData)

            data["testcase"] = testCaseData
            data["testcase_isbinary"] = isBinary
            data["testcase_quality"] = testCaseQuality
            data["testcase_size"] = testCaseSize
            data["testcase_ext"] = os.path.splitext(testCase)[1].lstrip(".")

        data["platform"] = crashInfo.configuration.platform
        data["product"] = crashInfo.configuration.product
        data["os"] = crashInfo.configuration.os

        if crashInfo.configuration.version:
            data["product_version"] = crashInfo.configuration.version

        data["client"] = self.clientId
        data["tool"] = self.tool

        if crashInfo.configuration.metadata or metaData:
            aggrMetaData = {}

            if crashInfo.configuration.metadata:
                aggrMetaData.update(crashInfo.configuration.metadata)

            if metaData:
                aggrMetaData.update(metaData)

            data["metadata"] = json.dumps(aggrMetaData)

        if crashInfo.configuration.env:
            data["env"] = json.dumps(crashInfo.configuration.env)

        if crashInfo.configuration.args:
            data["args"] = json.dumps(crashInfo.configuration.args)

        return self.post(url, data).json()

    @signature_checks
    def search(self, crashInfo):
        """
        Searches within the local signature cache directory for a signature matching the
        given crash.

        @type crashInfo: CrashInfo
        @param crashInfo: CrashInfo instance obtained from L{CrashInfo.fromRawCrashData}

        @rtype: tuple
        @return: Tuple containing filename of the signature and metadata matching, or
                 None if no match.
        """

        cachedSigFiles = os.listdir(self.sigCacheDir)

        for sigFile in cachedSigFiles:
            if not sigFile.endswith(".signature"):
                continue

            sigFile = os.path.join(self.sigCacheDir, sigFile)
            if not os.path.isdir(sigFile):
                with open(sigFile) as f:
                    sigData = f.read()
                    crashSig = CrashSignature(sigData)
                    if crashSig.matches(crashInfo):
                        metadataFile = sigFile.replace(".signature", ".metadata")
                        metadata = None
                        if os.path.exists(metadataFile):
                            with open(metadataFile) as m:
                                metadata = json.loads(m.read())

                        return (sigFile, metadata)

        return (None, None)

    @signature_checks
    def generate(
        self,
        crashInfo,
        forceCrashAddress=None,
        forceCrashInstruction=None,
        numFrames=None,
    ):
        """
        Generates a signature in the local cache directory. It will be deleted when
        L{refresh} is called on the same local cache directory.

        @type crashInfo: CrashInfo
        @param crashInfo: CrashInfo instance obtained from L{CrashInfo.fromRawCrashData}

        @type forceCrashAddress: bool
        @param forceCrashAddress: Force including the crash address into the signature
        @type forceCrashInstruction: bool
        @param forceCrashInstruction: Force including the crash instruction into the
                                      signature (GDB only)
        @type numFrames: int
        @param numFrames: How many frames to include in the signature

        @rtype: string
        @return: File containing crash signature in JSON format
        """

        sig = crashInfo.createCrashSignature(
            forceCrashAddress, forceCrashInstruction, numFrames
        )

        if not sig:
            return None

        # Write the file to a unique file name
        return self.__store_signature_hashed(sig)

    @remote_checks
    def download(self, crashId, crashJson=None):
        """
        Download the testcase for the specified crashId.

        @type crashId: int
        @param crashId: ID of the requested crash entry on the server side
        @type crashJson: dict
        @param crashJson: (optional) FM crash data to skip requesting it here

        @rtype: tuple
        @return: Tuple containing name of the file where the test was stored and the raw
                 JSON response
        """
        url = "%s://%s:%d/crashmanager/rest/crashes/%s/" % (
            self.serverProtocol,
            self.serverHost,
            self.serverPort,
            crashId,
        )

        dlurl = "%s://%s:%d/crashmanager/rest/crashes/%s/download/" % (
            self.serverProtocol,
            self.serverHost,
            self.serverPort,
            crashId,
        )
        if not crashJson:
            resp_json = self.get(url).json()
            if not isinstance(resp_json, dict):
                raise RuntimeError(
                    f"Server sent malformed JSON response: {resp_json!r}"
                )
        else:
            resp_json = crashJson

        if "testcase" not in resp_json or resp_json["testcase"] == "":
            print(
                f"Testcase not found for crash {resp_json.get('id', '[no ID]')}",
                file=sys.stderr,
            )
            return (None, resp_json)

        response = self.get(dlurl)

        if "content-disposition" not in response.headers:
            raise RuntimeError(f"Server sent malformed response: {response!r}")

        local_filename = f"{crashId}{os.path.splitext(resp_json['testcase'])[1]}"
        local_filename += (
            "bin"
            if resp_json.get("testcase_isbinary") and local_filename.endswith(".")
            else ""
        )

        with open(local_filename, "wb") as output:
            output.write(response.content)

        return (local_filename, resp_json)

    @remote_checks
    def download_all(self, query_params):
        """
        Download all testcases for the specified params.

        @type params: dict
        @param params: dictionary of params to download testcases for

        @rtype: generator
        @return: generator of filenames where tests were stored.
        """
        # iterate over each page
        for response in self.get_by_query("crashes/", query_params):
            resp_json = response

            for crash in resp_json["results"]:
                # crash here must already have same data as individual resp by crash ID
                (local_filename, resp_dl) = self.download(crash["id"], crash)
                if not local_filename:
                    continue

                yield local_filename

    @remote_checks
    def get_by_query(self, rest_endpoint, query_params={}, _ignore_toolfilter=None):
        """
        Get request for the specified REST endpoint and query params.

        @type rest_endpoint: str
        @param rest_endpoint: for crashmanager/rest/{rest_endpoint}.

        @type query_params: dict
        @param query_params: dictionary of params to query with; empty default.

        @type _ignore_toolfilter: int
        @param _ignore_toolfilter: integer 0 or 1 to ignore your set toolfilter
        @rtype: generator
        @return: generator of JSON responses for the specified query.
        """
        url_rest = "%s://%s:%d/crashmanager/rest/" % (
            self.serverProtocol,
            self.serverHost,
            self.serverPort,
        )
        next_url = url_rest + rest_endpoint
        global ignore_toolfilter
        ignore = (
            _ignore_toolfilter if _ignore_toolfilter is not None else ignore_toolfilter
        )
        params = {
            "query": json.dumps({"op": "AND", **query_params}),
            "ignore_toolfilter": ignore,
        }

        while next_url:
            resp_json = self.get(next_url, params=params).json()
            if not (isinstance(resp_json, dict) or isinstance(resp_json[0], dict)):
                raise RuntimeError(
                    f"Server sent malformed JSON response: {resp_json!r}"
                )
            if len(resp_json) == 0 or (
                isinstance(resp_json, dict) and resp_json.get("count") == 0
            ):
                print(
                    f"Results not found for {query_params} at {next_url}.",
                    file=sys.stderr,
                )
                continue

            if isinstance(resp_json, list):
                next_url = resp_json[0].get("next")
            else:
                next_url = resp_json.get("next")
            params = None
            yield resp_json

    def __store_signature_hashed(self, signature):
        """
        Store a signature, using the sha1 hash hex representation as filename.

        @type signature: CrashSignature
        @param signature: CrashSignature to store

        @rtype: string
        @return: Name of the file that the signature was written to

        """
        h = hashlib.new("sha1")
        if str is bytes:
            h.update(str(signature))
        else:
            h.update(str(signature).encode("utf-8"))
        sigfile = os.path.join(self.sigCacheDir, h.hexdigest() + ".signature")
        with open(sigfile, "w") as f:
            f.write(str(signature))

        return sigfile

    @staticmethod
    def read_testcase(testCase):
        """
        Read a testcase file, return the content and indicate if it is binary or not.

        @type testCase: string
        @param testCase: Filename of the file to open

        @rtype: tuple(string, bool)
        @return: Tuple containing the file contents and a boolean indicating if the
                 content is binary
        """
        with open(testCase, "rb") as f:
            testCaseData = f.read()

        noopBytes = bytearray(range(0x100))
        textBytes = bytearray([7, 8, 9, 10, 12, 13, 27]) + bytearray(range(0x20, 0x100))
        isBinary = bool(testCaseData.translate(noopBytes, textBytes))

        return (testCaseData, isBinary)


def main(args=None):
    """Command line options."""

    # setup argparser
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--version",
        action="version",
        version=f"{__file__} v{__version__} ({__updated__})",
    )

    # Crash information
    parser.add_argument("--stdout", help="File containing STDOUT data", metavar="FILE")
    parser.add_argument("--stderr", help="File containing STDERR data", metavar="FILE")
    parser.add_argument(
        "--crashdata", help="File containing external crash data", metavar="FILE"
    )

    # Actions
    action_group = parser.add_argument_group(
        "Actions", "A single action must be selected."
    )
    actions = action_group.add_mutually_exclusive_group(required=True)
    actions.add_argument(
        "--refresh", action="store_true", help="Perform a signature refresh"
    )
    actions.add_argument(
        "--submit", action="store_true", help="Submit a signature to the server"
    )
    actions.add_argument(
        "--search",
        action="store_true",
        help="Search cached signatures for the given crash",
    )
    actions.add_argument(
        "--generate",
        action="store_true",
        help="Create a (temporary) local signature in the cache directory",
    )
    actions.add_argument(
        "--autosubmit",
        action="store_true",
        help=(
            "Go into auto-submit mode. In this mode, all remaining arguments are "
            "interpreted as the crashing command. This tool will automatically obtain "
            "GDB crash information and submit it."
        ),
    )
    actions.add_argument(
        "--download",
        type=int,
        help="Download the testcase for the specified crash entry",
        metavar="ID",
    )
    actions.add_argument(
        "--download-all",
        type=int,
        help="Download all testcases for the specified signature entry",
        metavar="ID",
    )
    actions.add_argument(
        "--download-by-params",
        action="store_true",
        help="Download all testcases for the crashes specified by --query-params",
    )
    actions.add_argument(
        "--refresh-crashes",
        action="store_true",
        help="Refresh (download, resubmit) all testcases specified by --query-params",
    )
    actions.add_argument(
        "--get-clientid",
        action="store_true",
        help="Print the client ID used when submitting issues",
    )

    # Settings
    parser.add_argument("--sigdir", help="Signature cache directory", metavar="DIR")
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
        "--clientid", help="Client ID to use when submitting issues", metavar="ID"
    )
    parser.add_argument(
        "--platform", help="Platform this crash appeared on", metavar="(x86|x86-64|arm)"
    )
    parser.add_argument(
        "--product", help="Product this crash appeared on", metavar="PRODUCT"
    )
    parser.add_argument(
        "--productversion",
        dest="product_version",
        help="Product version this crash appeared on",
        metavar="VERSION",
    )
    parser.add_argument(
        "--os",
        help="OS this crash appeared on",
        metavar="(windows|linux|macosx|b2g|android)",
    )
    parser.add_argument(
        "--tool", help="Name of the tool that found this issue", metavar="NAME"
    )
    parser.add_argument(
        "--args",
        nargs="+",
        type=str,
        help=(
            "List of program arguments. Backslashes can be used for escaping and are "
            "stripped."
        ),
    )
    parser.add_argument(
        "--env",
        nargs="+",
        action=KeyValueAction,
        help="List of environment variables in the form 'KEY=VALUE'",
    )
    parser.add_argument(
        "--query-params",
        nargs="+",
        action=KeyValueAction,
        help="""Specify query params (key=value) to download/resubmit crashes:
        args, bucket, bucket_id, cachedCrashInfo, client, client_id, crashAddress,
        crashAddressNumeric, created, env, id, metadata, os, os_id, platform,
        platform_id, product, product_id, rawCrashData, rawStderr, rawStdout,
        shortSignature, testcase, testcase_id, tool, tool_id, triagedOnce. Instead, you
        can also get all crashes in your buckets (tool filter) with bucket=MYBUCKETS""",
    )
    parser.add_argument(
        "--best-entry-only",
        action="store_true",
        help="Refresh only the best entry crashes for buckets found by --query-params",
    )
    parser.add_argument(
        "--ignore-toolfilter",
        action="store_true",
        help="Ignore your (supposedly) set toolfilter for queries.",
    )
    parser.add_argument(
        "--metadata",
        nargs="+",
        action=KeyValueAction,
        help="List of metadata variables in the form 'KEY=VALUE'",
    )
    parser.add_argument(
        "--binary",
        help="Binary that has a configuration file for reading",
        metavar="BINARY",
    )

    parser.add_argument("--testcase", help="File containing testcase", metavar="FILE")
    parser.add_argument(
        "--testcasequality",
        default=0,
        type=int,
        help="Integer indicating test case quality (%(default)s is best and default)",
        metavar="VAL",
    )
    parser.add_argument(
        "--testcasesize",
        type=int,
        help="Integer indicating test case size (default is size of testcase data)",
        metavar="SIZE",
    )

    # Options that affect how signatures are generated
    parser.add_argument(
        "--forcecrashaddr",
        action="store_true",
        help="Force including the crash address into the signature",
    )
    parser.add_argument(
        "--forcecrashinst",
        action="store_true",
        help="Force including the crash instruction into the signature (GDB only)",
    )
    parser.add_argument(
        "--numframes",
        default=8,
        type=int,
        help="How many frames to include into the signature (default: %(default)s)",
    )

    parser.add_argument("rargs", nargs=argparse.REMAINDER)

    # process options
    opts = parser.parse_args(args=args)

    # In autosubmit mode, we try to open a configuration file for the binary specified
    # on the command line. It should contain the binary-specific settings for
    # submitting.
    if opts.autosubmit or opts.refresh_crashes:
        # Store the binary candidate only if --binary wasn't also specified
        if not opts.binary:
            opts.binary = opts.rargs[0]
    if opts.autosubmit:
        if not opts.rargs:
            parser.error("Action --autosubmit requires test arguments to be specified")

        # We also need to check that (apart from the binary), there is only one file on
        # the command line (the testcase), if it hasn't been explicitly specified.
        testcase = opts.testcase
        testcaseidx = None
        if testcase is None:
            for idx, arg in enumerate(opts.rargs[1:]):
                if os.path.exists(arg):
                    if testcase:
                        parser.error(
                            "Multiple potential testcases specified on command line. "
                            "Must explicitly specify test using --testcase."
                        )
                    testcase = arg
                    testcaseidx = idx

    # Either --autosubmit was specified, or someone specified --binary manually
    # Check that the binary actually exists
    if opts.binary and not os.path.exists(opts.binary):
        parser.error(f"Error: Specified binary does not exist: {opts.binary}")

    stdout = None
    stderr = None
    crashdata = None
    crashInfo = None
    args = None
    metadata = opts.metadata if opts.metadata else {}

    if (
        opts.search
        or opts.generate
        or opts.submit
        or opts.autosubmit
        or opts.refresh_crashes
    ):
        if opts.autosubmit:
            # Try to automatically get arguments from the command line
            # If the testcase is not the last argument, leave it in the
            # command line arguments and replace it with a generic placeholder.
            if testcaseidx == len(opts.rargs[1:]) - 1:
                args = opts.rargs[1:-1]
            else:
                args = opts.rargs[1:]
                if testcaseidx is not None:
                    args[testcaseidx] = "TESTFILE"
        else:
            if opts.args:
                args = [arg.replace("\\", "") for arg in opts.args]

        # Start without any ProgramConfiguration
        configuration = None

        # If we have a binary, try using that to create our ProgramConfiguration
        if opts.binary:
            configuration = ProgramConfiguration.fromBinary(opts.binary)
            if configuration:
                if opts.env:
                    configuration.addEnvironmentVariables(opts.env)
                if args:
                    configuration.addProgramArguments(args)
                if metadata:
                    configuration.addMetadata(metadata)

        # If configuring through binary failed, try to manually create
        # ProgramConfiguration from command line arguments
        if configuration is None:
            if opts.platform is None or opts.product is None or opts.os is None:
                parser.error(
                    "Must specify/configure at least --platform, --product and --os"
                )

            configuration = ProgramConfiguration(
                opts.product,
                opts.platform,
                opts.os,
                opts.product_version,
                opts.env,
                args,
                metadata,
            )

        if not opts.autosubmit and not opts.refresh_crashes:
            if opts.stderr is None and opts.crashdata is None:
                parser.error(
                    "Must specify at least either --stderr or --crashdata file"
                )

            if opts.stdout:
                with open(opts.stdout) as f:
                    stdout = f.read()

            if opts.stderr:
                with open(opts.stderr) as f:
                    stderr = f.read()

            if opts.crashdata:
                with open(opts.crashdata) as f:
                    crashdata = f.read()

            crashInfo = CrashInfo.fromRawCrashData(
                stdout, stderr, configuration, auxCrashData=crashdata
            )
            if opts.testcase:
                (testCaseData, isBinary) = Collector.read_testcase(opts.testcase)
                if not isBinary:
                    crashInfo.testcase = testCaseData

    serverauthtoken = None
    if opts.serverauthtokenfile:
        with open(opts.serverauthtokenfile) as f:
            serverauthtoken = f.read().rstrip()

    collector = Collector(
        opts.sigdir,
        opts.serverhost,
        opts.serverport,
        opts.serverproto,
        serverauthtoken,
        opts.clientid,
        opts.tool,
    )
    url_rest = "%s://%s:%d/crashmanager/rest/" % (
        collector.serverProtocol,
        collector.serverHost,
        collector.serverPort,
    )
    global ignore_toolfilter
    ignore_toolfilter = 1 if opts.ignore_toolfilter else 0

    if opts.refresh:
        collector.refresh()
        return 0

    if opts.submit:
        testcase = opts.testcase
        collector.submit(
            crashInfo, testcase, opts.testcasequality, opts.testcasesize, metadata
        )
        return 0

    if opts.search:
        (sig, metadata) = collector.search(crashInfo)
        if sig is None:
            print("No match found", file=sys.stderr)
            return 3
        print(sig)
        if metadata:
            print(json.dumps(metadata, indent=4))
        return 0

    if opts.generate:
        sigFile = collector.generate(
            crashInfo, opts.forcecrashaddr, opts.forcecrashinst, opts.numframes
        )
        if not sigFile:
            print(
                "Failed to generate a signature for the given crash information.",
                file=sys.stderr,
            )
            return 1
        print(sigFile)
        return 0

    if opts.autosubmit:
        runner = AutoRunner.fromBinaryArgs(opts.rargs[0], opts.rargs[1:])
        if runner.run():
            crashInfo = runner.getCrashInfo(configuration)
            collector.submit(
                crashInfo, testcase, opts.testcasequality, opts.testcasesize, metadata
            )
        else:
            print(
                "Error: Failed to reproduce the given crash, cannot submit.",
                file=sys.stderr,
            )
            return 1

    if opts.download:
        (retFile, retJSON) = collector.download(opts.download)
        if not retFile:
            print("Specified crash entry does not have a testcase", file=sys.stderr)
            return 1

        if "args" in retJSON and retJSON["args"]:
            args = json.loads(retJSON["args"])
            print(
                "Command line arguments:",
                " ".join(args),
            )
            print("")

        if "env" in retJSON and retJSON["env"]:
            opts.env = json.loads(retJSON["env"])
            print(
                "Environment variables:",
                " ".join(f"{k} = {v}" for (k, v) in opts.env.items()),
            )
            print("")

        if "metadata" in retJSON and retJSON["metadata"]:
            metadata = json.loads(retJSON["metadata"])
            print("== Metadata ==")
            for k, v in metadata.items():
                print(f"{k} = {v}")
            print("")

        print(retFile)
        return 0

    if opts.download_all:
        downloaded = False

        for result in collector.download_all({"bucket": opts.download_all}):
            downloaded = True
            print("Downloaded: ", result)

        if not downloaded:
            print("Specified signature does not have any testcases", file=sys.stderr)
            return 1

        return 0

    if opts.query_params.get("bucket") == "MYBUCKETS":
        if len(opts.query_params) > 1:
            print("Can't use other query params w/ bucket=MYBUCKETS", file=sys.stderr)
            return 1
        # ignore all other query params when mybuckets is used
        nobuckets = True
        buckets = set()
        for response in collector.get_by_query("buckets/"):
            if len(response) > 0:
                nobuckets = False
            for bucket in response:
                buckets.add(bucket["id"])
        if nobuckets:
            print("No buckets found", file=sys.stderr)
            return 1
        all_params = [{"bucket": bucket} for bucket in buckets]
    elif opts.query_params:
        if opts.best_entry_only:
            buckets = set()
            for response in collector.get_by_query("crashes/", opts.query_params):
                for crash in response["results"]:
                    buckets.add(crash["bucket"])
        else:
            all_params = [opts.query_params]

    if opts.best_entry_only:
        all_params = []
        for bucket in buckets:
            resp_bucket = collector.get(
                url_rest + f"buckets/{bucket}",
                params={"ignore_toolfilter": ignore_toolfilter},
            ).json()
            all_params.append({"bucket": bucket, "id": resp_bucket["best_entry"]})

    if opts.download_by_params:
        downloaded = False

        if not opts.query_params:
            print("Specify query params to download testcases", file=sys.stderr)
            return 1

        for param in all_params:
            for result in collector.download_all(param):
                downloaded = True
                print("Downloaded: ", result)

        if not downloaded:
            print("Failed to download testcases for the specified params")

    if opts.refresh_crashes:
        if not opts.query_params:
            print("Specify query params to refresh crashes.", file=sys.stderr)
            return 1

        for param in all_params:
            for testcase in collector.download_all(param):
                # TODO: support positional testcases (e.g. for libfuzzer)
                os.environ["MOZ_FUZZ_TESTFILE"] = testcase  # needed by AFL++
                runner = AutoRunner.fromBinaryArgs(opts.binary, opts.rargs[1:])
                # TODO: diff old vs new crash?
                ran = runner.run()
                if ran:
                    crashInfo = runner.getCrashInfo(configuration)
                    submission = collector.submit(
                        crashInfo,
                        testcase,
                        opts.testcasequality,
                        opts.testcasesize,
                        metadata,
                    )
                    print(
                        "Resubmitted old crash {} as {}.".format(
                            os.path.splitext(testcase)[0], submission["id"]
                        )
                    )
                else:
                    print(
                        "Error: Failed to reproduce crash %s, can't submit."
                        % os.path.splitext(testcase)[0],
                        file=sys.stderr,
                    )
        return 0

    if opts.get_clientid:
        print(collector.clientId)
        return 0


if __name__ == "__main__":
    sys.exit(main())
