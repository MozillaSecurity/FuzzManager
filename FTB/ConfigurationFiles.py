# encoding: utf-8
'''
ConfigurationFiles -- Generic class used in FuzzManager to read one or more configuration files

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

from six.moves import configparser


class ConfigurationFiles():
    def __init__(self, configFiles):
        self.mainConfig = {}
        self.metadataConfig = {}

        if configFiles:
            self.parser = configparser.ConfigParser()

            # Make sure keys are kept case-sensitive
            self.parser.optionxform = str

            self.parser.read(configFiles)
            self.mainConfig = self.getSectionMap("Main")
            self.metadataConfig = self.getSectionMap("Metadata")

            # Produce warnings for unrecognized sections to make
            # debugging easier. Especially main vs. Main is hard
            # to figure out sometimes.
            sections = self.parser.sections()
            for section in ["Main", "Metadata"]:
                if section in sections:
                    sections.remove(section)
            if sections:
                print("Warning: Ignoring the following config file sections: %s" % " ".join(sections), file=sys.stderr)

    def getSectionMap(self, section):
        ret = {}
        try:
            options = self.parser.options(section)
        except configparser.NoSectionError:
            return {}
        for o in options:
            ret[o] = self.parser.get(section, o)
        return ret
