# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import json
import re
from abc import ABC, abstractmethod
from typing import Any

from dateutil.parser import isoparse
from jsonpath_ng import parse as jsonpath


class Symptom(ABC):
    """Abstract base class that provides a method to instantiate the right sub-class.
    It also supports generating a Signature based on the stored information.
    """

    def __init__(self, json_obj):
        self.json_obj = json_obj

    def __str__(self):
        return json.dumps(self.json_obj, indent=2)

    @staticmethod
    def order(symptom):
        """Estimate a complexity for Symptoms.
        Ordering by complexity makes matching faster.
        """
        if isinstance(symptom, StringMatchSymptom):
            if symptom.matcher.is_re:
                return 1
            return 0
        if isinstance(symptom, URLMatchSymptom):
            return 2
        if isinstance(symptom, ReportedMatchSymptom):
            if symptom.time is not None:
                return 3
            return 4
        if isinstance(symptom, JSONPathSymptom):
            if symptom.path is None:
                if symptom.matcher.is_re:
                    return 6
                return 5
            if symptom.matcher.is_re:
                return 8
            return 7
        raise RuntimeError(f"Unhandled Symptom type: {type(symptom).__name__}")

    @staticmethod
    def load(obj: dict[str, Any]) -> "Symptom":
        """Create the appropriate Symptom based on the given object (decoded from JSON)

        Arguments:
            obj
        @type obj: map
        @param obj: Object as decoded from JSON

        @rtype: Symptom
        @return: Symptom subclass instance matching the given object
        """

        stype = obj["type"]

        if stype in {
            "app_channel",
            "app_name",
            "app_version",
            "breakage_category",
            "comments",
            "os",
            "uuid",
        }:
            return StringMatchSymptom(obj)
        elif stype == "url":
            return URLMatchSymptom(obj)
        elif stype == "reported_at":
            return ReportedMatchSymptom(obj)
        elif stype == "details":
            return JSONPathSymptom(obj)
        else:
            raise RuntimeError(f"Unknown symptom type: {stype}")

    @abstractmethod
    def matches(self, report) -> bool:
        """
        Check if the symptom matches the given report information

        @type reportInfo: ReportInfo
        @param reportInfo: The report information to check against

        @rtype: bool
        @return: True if the symptom matches, False otherwise
        """


class _PatternMatcher:
    def __init__(self, pattern):
        if pattern.startswith("/") and pattern.endswith("/"):
            self.pattern = re.compile(pattern[1:-1])
            self.is_re = True
        else:
            self.pattern = pattern
            self.is_re = False

    def matches(self, value):
        if self.is_re:
            return self.pattern.match(value) is not None
        return self.pattern == value


class StringMatchSymptom(Symptom):
    def __init__(self, obj):
        super().__init__(obj)
        self.attr = obj["type"]
        self.matcher = _PatternMatcher(obj["value"])

    def matches(self, report) -> bool:
        return self.matcher.matches(getattr(report, self.attr))


class URLMatchSymptom(Symptom):
    def __init__(self, obj):
        super().__init__(obj)
        self.part = obj.get("part")
        self.matcher = _PatternMatcher(obj["value"])

    def matches(self, report) -> bool:
        if self.part is None:
            value = report.url.geturl()
        else:
            value = getattr(report.url, self.part)
        return self.matcher.matches(value)


class ReportedMatchSymptom(Symptom):
    def __init__(self, obj):
        super().__init__(obj)
        if "before" in obj:
            self.before = isoparse(obj["before"])
        else:
            self.before = None
        if "after" in obj:
            self.after = isoparse(obj["after"])
        else:
            self.after = None
        if "time" in obj:
            self.time = isoparse(obj["time"])
        else:
            self.time = None

    def matches(self, report) -> bool:
        if self.time is not None:
            return report.reported_at == self.time
        if self.after is not None and report.reported_at <= self.after:
            return False
        if self.before is not None and report.reported_at >= self.before:
            return False
        return True


class JSONPathSymptom(Symptom):
    def __init__(self, obj):
        super().__init__(obj)
        if "path" in obj:
            self.path = jsonpath(obj["path"])
        else:
            self.path = None
        self.matcher = _PatternMatcher(obj["value"])

    def matches(self, report) -> bool:
        if self.path is None:
            return self.matcher.matches(json.dumps(report.details))
        # iterate over the jsonpath values
        return any(
            self.matcher.matches(value) for value in self.path.find(report.details)
        )
