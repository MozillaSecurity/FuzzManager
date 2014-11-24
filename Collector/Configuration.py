#!/usr/bin/env python
# encoding: utf-8
'''
BuildConfig -- Represents one build configuration

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''

# Ensure print() compatibility with Python 3
from __future__ import print_function

try:
    import configparser
except ImportError:
    import ConfigParser as configparser

import sys
import os

BASE_DIR = os.path.dirname(os.path.realpath(__file__))
FTB_PATH = os.path.abspath(os.path.join(BASE_DIR, ".."))
sys.path += [FTB_PATH]

class Configuration():
    def __init__(self, configFiles):
        self.mainConfig = {}
        self.metadataConfig = {}
        
        if configFiles:
            self.parser = configparser.ConfigParser()
            self.parser.read(configFiles)
            self.mainConfig = self.getSectionMap("Main")
            self.metadataConfig = self.getSectionMap("Metadata")
        
    def getSectionMap(self, section):
        ret = {}
        try:
            options = self.parser.options(section)
        except configparser.NoSectionError, e:
            return {}
        for o in options:
            ret[o] = self.parser.get(section, o)
        return ret