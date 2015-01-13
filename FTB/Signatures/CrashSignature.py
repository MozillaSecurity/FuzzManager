'''
Crash Signature

Represents a crash signature as specified in https://wiki.mozilla.org/Security/CrashSignatures

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''

import json
from FTB.Signatures import JSONHelper
from FTB.Signatures.Symptom import Symptom, TestcaseSymptom

class CrashSignature():
    def __init__(self, rawSignature):
        '''
        Constructor
        
        @type rawSignature: string
        @param rawSignature: A JSON-formatted string representing the crash signature
        '''
        
        # For now, we store the original raw signature and hand it out for
        # conversion to String. This is fine as long as our Signature object
        # is immutable. Later, we should implement a method that actually
        # serializes this object back to JSON as it is.
        #
        self.rawSignature = rawSignature
        self.symptoms = []
        
        try:
            obj = json.loads(rawSignature)
        except ValueError, e:
            raise RuntimeError("Invalid JSON: %s" % e)
        
        # Get the symptoms objects (mandatory)
        if "symptoms" in obj:
            symptoms = JSONHelper.getArrayChecked(obj, "symptoms", True)
            if len(symptoms) == 0:
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
    def fromFile(signatureFile):
        with open(signatureFile, 'r') as sigFd:
            return CrashSignature(sigFd.read())
    
    def __str__(self):
        return self.rawSignature
    
    def matches(self, crashInfo):
        '''
        Match this signature against the given crash information
        
        @type crashInfo: CrashInfo
        @param crashInfo: The crash info to match the signature against
        
        @rtype: bool
        @return: True if the signature matches, False otherwise
        '''
        if self.platforms != None and not crashInfo.platform in self.platforms:
            return False
        
        if self.operatingSystems != None and not crashInfo.os in self.operatingSystems:
            return False
        
        if self.products != None and not crashInfo.product in self.products:
            return False
        
        for symptom in self.symptoms:
            if not symptom.matches(crashInfo):
                return False
        
        return True
    
    def matchRequiresTest(self):
        '''
        Check if the signature requires a testcase to match.
        
        This method can be used to avoid attaching a testcase to the crashInfo
        before matching, avoiding unnecessary I/O on testcase files.
        
        @rtype: bool
        @return: True if the signature requires a testcase to match
        '''
        for symptom in self.symptoms:
            if isinstance(symptom, TestcaseSymptom):
                return True
        
        return False
    
    def getOffendingSymptoms(self, crashInfo):
        offendingSymptoms = []
        for symptom in self.symptoms:
            if not symptom.matches(crashInfo):
                offendingSymptoms.append(symptom)
        return offendingSymptoms
    
    def getSymptomsDiff(self, crashInfo):
        symptomsDiff = []
        for symptom in self.symptoms:
            if symptom.matches(crashInfo):
                symptomsDiff.append({ 'offending' : False, 'symptom' : symptom })
            else:
                symptomsDiff.append({ 'offending' : True, 'symptom' : symptom })
        return symptomsDiff