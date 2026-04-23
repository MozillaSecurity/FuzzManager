"""
Crash Signature

Represents a crash signature as specified in
https://wiki.mozilla.org/Security/CrashSignatures

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
"""

from __future__ import annotations

import difflib
import json
from typing import TYPE_CHECKING, Any

from FTB.Signatures import JSONHelper
from FTB.Signatures.Symptom import (
    OutputSymptom,
    StackFramesSymptom,
    Symptom,
    TestcaseSymptom,
)

if TYPE_CHECKING:
    from FTB.Signatures.CrashInfo import CrashInfo


class CrashSignature:
    def __init__(self, rawSignature: str) -> None:
        """
        Constructor

        @type rawSignature: string
        @param rawSignature: A JSON-formatted string representing the crash signature
        """

        # For now, we store the original raw signature and hand it out for
        # conversion to String. This is fine as long as our Signature object
        # is immutable. Later, we should implement a method that actually
        # serializes this object back to JSON as it is.
        #
        self.rawSignature = rawSignature
        self.symptoms: list[Symptom] = []

        try:
            obj = json.loads(rawSignature)
        except ValueError as e:
            raise RuntimeError(f"Invalid JSON: {e}")

        # Get the symptoms objects (mandatory)
        if "symptoms" in obj:
            symptoms = JSONHelper.getArrayChecked(obj, "symptoms", True)
            if not symptoms:
                raise RuntimeError("Signature must have at least one symptom.")

            for rawSymptomsObj in symptoms:
                self.symptoms.append(Symptom.fromJSONObject(rawSymptomsObj))
        else:
            raise RuntimeError('Missing mandatory top-level key "symptoms".')

        # Get some optional lists
        self.platforms = JSONHelper.getArrayChecked(obj, "platforms")
        self.operatingSystems = JSONHelper.getArrayChecked(obj, "operatingSystems")
        self.products = JSONHelper.getArrayChecked(obj, "products")

    @staticmethod
    def fromFile(signatureFile: str) -> CrashSignature:
        with open(signatureFile) as sigFd:
            return CrashSignature(sigFd.read())

    def __str__(self) -> str:
        return self.rawSignature

    def matches(self, crashInfo: CrashInfo) -> bool:
        """
        Match this signature against the given crash information

        @type crashInfo: CrashInfo
        @param crashInfo: The crash info to match the signature against

        @rtype: bool
        @return: True if the signature matches, False otherwise
        """
        if self.platforms is not None:
            assert crashInfo.configuration is not None
            if crashInfo.configuration.platform not in self.platforms:
                return False
        if self.operatingSystems is not None:
            assert crashInfo.configuration is not None
            if crashInfo.configuration.os not in self.operatingSystems:
                return False
        if self.products is not None:
            assert crashInfo.configuration is not None
            if crashInfo.configuration.product not in self.products:
                return False

        deferredSymptoms = []

        for symptom in self.symptoms:
            # We want to defer matching Testcase and Output symptoms as they can be slow
            # and pretty much all other symptoms are instant in matching.
            if isinstance(symptom, (TestcaseSymptom, OutputSymptom)):
                deferredSymptoms.append(symptom)
                continue

            if not symptom.matches(crashInfo):
                return False

        return all(symptom.matches(crashInfo) for symptom in deferredSymptoms)

    def matchRequiresTest(self) -> bool:
        """
        Check if the signature requires a testcase to match.

        This method can be used to avoid attaching a testcase to the crashInfo
        before matching, avoiding unnecessary I/O on testcase files.

        @rtype: bool
        @return: True if the signature requires a testcase to match
        """
        return any(isinstance(symptom, TestcaseSymptom) for symptom in self.symptoms)

    def getRequiredOutputSources(self) -> list[str]:
        """
        Return a list of output sources required by this signature for matching.

        This method can be used to avoid loading raw output fields from the
        database if they are not required for the particular signature.

        @rtype: list(str)
        @return: A list of output identifiers (e.g. stdout, stderr or crashdata)
                 required by this signature.
        """
        ret: list[str] = []

        for symptom in self.symptoms:
            if isinstance(symptom, OutputSymptom):
                if symptom.src is None:
                    # If src is not specified in the signature, the default
                    # is to match all available output sources.
                    return ["stdout", "stderr", "crashdata"]
                ret.append(symptom.src)

        return ret

    def getDistance(self, crashInfo: CrashInfo) -> int:
        distance = 0

        for symptom in self.symptoms:
            if isinstance(symptom, StackFramesSymptom):
                symptomDistance = symptom.diff(crashInfo)[0]
                if symptomDistance is not None:
                    distance += symptomDistance
                else:
                    # If we can't find the distance, assume worst-case
                    distance += len(symptom.functionNames)
            else:
                if not symptom.matches(crashInfo):
                    distance += 1

        if self.platforms is not None:
            assert crashInfo.configuration is not None
            if crashInfo.configuration.platform not in self.platforms:
                distance += 1
        if self.operatingSystems is not None:
            assert crashInfo.configuration is not None
            if crashInfo.configuration.os not in self.operatingSystems:
                distance += 1
        if self.products is not None:
            assert crashInfo.configuration is not None
            if crashInfo.configuration.product not in self.products:
                distance += 1

        return distance

    def fit(self, crashInfo: CrashInfo) -> CrashSignature | None:
        sigObj: dict[str, Any] = {}
        sigSymptoms: list[Any] = []

        sigObj["symptoms"] = sigSymptoms

        if self.platforms:
            sigObj["platforms"] = self.platforms

        if self.operatingSystems:
            sigObj["operatingSystems"] = self.operatingSystems

        if self.products:
            sigObj["products"] = self.products

        symptomsDiff = self.getSymptomsDiff(crashInfo)

        for symptomDiff in symptomsDiff:
            if symptomDiff["offending"]:
                if "proposed" in symptomDiff:
                    sigSymptoms.append(symptomDiff["proposed"].jsonobj)
            else:
                sigSymptoms.append(symptomDiff["symptom"].jsonobj)

        if not sigSymptoms:
            return None

        return CrashSignature(json.dumps(sigObj, indent=2, sort_keys=True))

    def getSymptomsDiff(self, crashInfo: CrashInfo) -> list[dict[str, Any]]:
        symptomsDiff: list[dict[str, Any]] = []
        for symptom in self.symptoms:
            if symptom.matches(crashInfo):
                symptomsDiff.append({"offending": False, "symptom": symptom})
            else:
                # Special-case StackFramesSymptom because we would like to get a
                # fine-grained view on the offending parts *inside* that symptom. By
                # calling matchWithDiff, we annotate internals of the symptom with
                # distance information to display.
                if isinstance(symptom, StackFramesSymptom):
                    proposedSymptom = symptom.diff(crashInfo)[1]
                    if proposedSymptom:
                        symptomsDiff.append(
                            {
                                "offending": True,
                                "symptom": symptom,
                                "proposed": proposedSymptom,
                            }
                        )
                        continue

                symptomsDiff.append({"offending": True, "symptom": symptom})
        return symptomsDiff

    def getSignatureUnifiedDiffTuples(
        self, crashInfo: CrashInfo
    ) -> list[tuple[str, str]]:
        diffTuples: list[tuple[str, str]] = []

        # go through dumps(loads()) to standardize the format.
        # the dumps args here must match what is returned by `fit()`
        oldLines = json.dumps(
            json.loads(self.rawSignature), indent=2, sort_keys=True
        ).splitlines()
        newLines = []
        newRawCrashSignature = self.fit(crashInfo)
        if newRawCrashSignature:
            newLines = newRawCrashSignature.rawSignature.splitlines()
        context = max(len(oldLines), len(newLines))

        signatureDiff = difflib.unified_diff(oldLines, newLines, n=context)

        for diffLine in signatureDiff:
            if (
                diffLine.startswith("+++")
                or diffLine.startswith("---")
                or diffLine.startswith("@@")
                or not diffLine.strip()
            ):
                continue

            diffTuples.append((diffLine[0], diffLine[1:]))

        return diffTuples
