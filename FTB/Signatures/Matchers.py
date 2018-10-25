'''
Matchers

Various matcher classes required by crash signatures

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''

# Ensure print() compatibility with Python 3
from __future__ import print_function, unicode_literals

from abc import ABCMeta, abstractmethod
import numbers
import re

import six

from FTB.Signatures import JSONHelper


@six.add_metaclass(ABCMeta)
class Match(object):

    @abstractmethod
    def matches(self, value):
        pass


class StringMatch(Match):

    def __init__(self, obj):
        self.isPCRE = False
        self.compiledValue = None
        self.patternContainsSlash = False

        if isinstance(obj, bytes):
            obj = obj.decode("utf-8")

        if isinstance(obj, six.text_type):
            self.value = obj

            # Support the short form using forward slashes to indicate a PCRE
            if self.value.startswith("/") and self.value.endswith("/"):
                self.isPCRE = True
                self.value = self.value[1:-1]
                self.patternContainsSlash = "/" in self.value
                try:
                    self.compiledValue = re.compile(self.value)
                except re.error as e:
                    raise RuntimeError("Error in regular expression: %s" % e)
        else:
            self.value = JSONHelper.getStringChecked(obj, "value", True)

            matchType = JSONHelper.getStringChecked(obj, "matchType", False)
            if matchType is not None:
                if matchType.lower() == "contains":
                    pass
                elif matchType.lower() == "pcre":
                    self.isPCRE = True
                    try:
                        self.compiledValue = re.compile(self.value)
                    except re.error as e:
                        raise RuntimeError("Error in regular expression: %s" % e)
                else:
                    raise RuntimeError("Unknown match operator specified: %s" % matchType)

    def matches(self, value, windowsSlashWorkaround=False):
        if isinstance(value, bytes):
            # If the input is not already unicode, try to interpret it as UTF-8
            # If there are errors, replace them with U+FFFD so we neither raise nor false positive.
            value = value.decode("utf-8", errors="replace")

        if self.isPCRE:
            if self.compiledValue.search(value) is not None:
                return True
            elif windowsSlashWorkaround and self.patternContainsSlash:
                # NB this will fail if the pattern is supposed to match a backslash and a windows-style path
                #    in the same line
                return self.compiledValue.search(value.replace("\\", "/")) is not None
            return False
        else:
            return self.value in value

    def __str__(self):
        return self.value

    def __repr__(self):
        if self.isPCRE:
            return '/%s/' % self.value

        return self.value


class NumberMatchType(object):
    GE, GT, LE, LT = range(4)


class NumberMatch(Match):

    def __init__(self, obj):
        self.matchType = None

        if isinstance(obj, bytes):
            obj = obj.decode("utf-8")

        if isinstance(obj, six.text_type):
            if len(obj) > 0:
                numberMatchComponents = obj.split(None, 1)
                numIdx = 0

                if len(numberMatchComponents) > 1:
                    numIdx = 1
                    matchType = numberMatchComponents[0]

                    if matchType == "==":
                        pass
                    elif matchType == "<":
                        self.matchType = NumberMatchType.LT
                    elif matchType == "<=":
                        self.matchType = NumberMatchType.LE
                    elif matchType == ">":
                        self.matchType = NumberMatchType.GT
                    elif matchType == ">=":
                        self.matchType = NumberMatchType.GE
                    else:
                        raise RuntimeError("Unknown match operator specified: %s" % matchType)

                try:
                    value = numberMatchComponents[numIdx]
                    base = 16 if value.startswith("0x") else 10
                    self.value = int(numberMatchComponents[numIdx], base)
                except ValueError:
                    raise RuntimeError("Invalid number specified: %s" % numberMatchComponents[numIdx])
            else:
                # We're trying to match the fact that we cannot calculate a crash address
                self.value = None

        elif isinstance(obj, numbers.Integral):
            self.value = obj
        else:
            raise RuntimeError("Invalid type %s in NumberMatch." % type(obj))

    def matches(self, value):
        if value is None:
            return self.value is None

        if self.matchType == NumberMatchType.GE:
            return value >= self.value
        elif self.matchType == NumberMatchType.GT:
            return value > self.value
        elif self.matchType == NumberMatchType.LE:
            return value <= self.value
        elif self.matchType == NumberMatchType.LT:
            return value < self.value
        else:
            return value == self.value
