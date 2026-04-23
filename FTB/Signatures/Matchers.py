"""
Matchers

Various matcher classes required by crash signatures

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
"""

import re
from abc import ABCMeta, abstractmethod
from enum import Enum
from typing import Any

from FTB.Signatures import JSONHelper


class Match(metaclass=ABCMeta):
    @abstractmethod
    def matches(self, value: Any) -> bool:
        pass


class StringMatch(Match):
    def __init__(self, obj: str | bytes | dict[str, Any]) -> None:
        self.isPCRE = False
        self.compiledValue: re.Pattern[str] | None = None
        self.patternContainsSlash = False

        if isinstance(obj, bytes):
            obj = obj.decode("utf-8")

        if isinstance(obj, str):
            self.value = obj

            # Support the short form using forward slashes to indicate a PCRE
            if self.value.startswith("/") and self.value.endswith("/"):
                self.isPCRE = True
                self.value = self.value[1:-1]
                self.patternContainsSlash = "/" in self.value
                try:
                    self.compiledValue = re.compile(self.value)
                except re.error as e:
                    raise RuntimeError(f"Error in regular expression: {e}")
        else:
            value = JSONHelper.getStringChecked(obj, "value", True)
            assert value is not None
            self.value = value

            matchType = JSONHelper.getStringChecked(obj, "matchType", False)
            if matchType is not None:
                if matchType.lower() == "contains":
                    pass
                elif matchType.lower() == "pcre":
                    self.isPCRE = True
                    try:
                        self.compiledValue = re.compile(self.value)
                    except re.error as e:
                        raise RuntimeError(f"Error in regular expression: {e}")
                else:
                    raise RuntimeError(f"Unknown match operator specified: {matchType}")

    def matches(self, value: str | bytes, windowsSlashWorkaround: bool = False) -> bool:
        if isinstance(value, bytes):
            # If the input is not already unicode, try to interpret it as UTF-8
            # If there are errors, replace them with U+FFFD so we neither raise nor
            # false positive.
            value = value.decode("utf-8", errors="replace")

        if self.isPCRE:
            assert self.compiledValue is not None
            if self.compiledValue.search(value) is not None:
                return True
            if windowsSlashWorkaround and self.patternContainsSlash:
                # NB this will fail if the pattern is supposed to match a backslash and
                #    a windows-style path in the same line
                return self.compiledValue.search(value.replace("\\", "/")) is not None
            return False
        return self.value in value

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        if self.isPCRE:
            return f"/{self.value}/"

        return self.value


# TODO: Python >= 3.11: Enum -> StrEnum
class NumberMatchType(str, Enum):
    EQ = "=="
    GE = ">="
    GT = ">"
    LE = "<="
    LT = "<"


class NumberMatch(Match):
    def __init__(self, obj: str | bytes | int) -> None:
        self.matchType: NumberMatchType | None = None
        self.value: int | None = None

        if isinstance(obj, bytes):
            obj = obj.decode("utf-8")

        if isinstance(obj, str):
            if len(obj) > 0:
                numberMatchComponents = obj.split(maxsplit=1)
                numIdx = 0

                if len(numberMatchComponents) > 1:
                    numIdx = 1
                    matchType = numberMatchComponents[0]
                    try:
                        self.matchType = NumberMatchType(matchType)
                    except ValueError:
                        raise RuntimeError(
                            f"Unknown match operator specified: {matchType}"
                        )

                try:
                    value = numberMatchComponents[numIdx]
                    base = 16 if value.startswith("0x") else 10
                    self.value = int(numberMatchComponents[numIdx], base)
                except ValueError:
                    raise RuntimeError(
                        f"Invalid number specified: {numberMatchComponents[numIdx]}"
                    )
            else:
                # We're trying to match the fact that we cannot calculate a crash
                # address
                self.value = None

        elif isinstance(obj, int):
            self.value = obj
        else:
            raise RuntimeError(f"Invalid type {type(obj)} in NumberMatch.")

    def matches(self, value: int | None) -> bool:
        if value is None:
            return self.value is None

        # _matchType is only set when __init__ parses a non-empty string that also
        # sets self.value, so these comparisons are safe.
        if self.matchType is not None:
            assert self.value is not None
            if self.matchType == NumberMatchType.GE:
                return value >= self.value
            if self.matchType == NumberMatchType.GT:
                return value > self.value
            if self.matchType == NumberMatchType.LE:
                return value <= self.value
            if self.matchType == NumberMatchType.LT:
                return value < self.value
        return value == self.value
