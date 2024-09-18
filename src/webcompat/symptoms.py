# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from __future__ import annotations

import inspect
import json
import re
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from logging import getLogger
from typing import TYPE_CHECKING, Any

from dateutil.parser import isoparse
from jsonpath_ng import parse as jsonpath  # type: ignore[import-untyped]

if TYPE_CHECKING:
    from .models import Report

LOG = getLogger(__file__)


class Symptom(ABC):
    """Abstract base class that provides a load method to instantiate the right
    sub-class.
    """

    ORDER: int

    def __init__(self, json_obj: dict[str, Any]) -> None:
        self.matcher: Matcher
        self.json_obj = json_obj

    def __str__(self):
        return json.dumps(self.json_obj, indent=2)

    @staticmethod
    def order(symptom: Symptom) -> int:
        """Estimate a complexity for Symptoms.
        Ordering by complexity makes matching faster.
        """
        return symptom.ORDER * (MAX_MATCHER_ORDER + 1) + symptom.matcher.ORDER

    @staticmethod
    def load(obj: dict[str, Any]) -> Symptom:
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
            return StringPropertySymptom(obj)
        if stype == "url":
            return URLSymptom(obj)
        if stype == "reported_at":
            return ReportedAtSymptom(obj)
        if stype == "details":
            return DetailsSymptom(obj)
        raise RuntimeError(f"Unknown symptom type: {stype}")  # pragma: no cover

    @abstractmethod
    def matches(self, report: Report) -> bool:
        """
        Check if the symptom matches the given report information

        @type reportInfo: ReportInfo
        @param reportInfo: The report information to check against

        @rtype: bool
        @return: True if the symptom matches, False otherwise
        """


class Matcher(ABC):
    ORDER: int

    @staticmethod
    def create(obj: dict[str, Any]) -> Matcher:
        if "value" in obj:
            if obj["value"] is None:
                return NullMatcher()
            return ValueMatcher(obj["value"])
        if "time" in obj:
            return TimeMatcher(isoparse(obj["time"]).replace(tzinfo=timezone.utc))
        if "pattern" in obj:
            return PatternMatcher(obj["pattern"])
        after = before = None
        if "before" in obj:
            before = isoparse(obj["before"]).replace(tzinfo=timezone.utc)
        if "after" in obj:
            after = isoparse(obj["after"]).replace(tzinfo=timezone.utc)
        return TimeRangeMatcher(after, before)

    @abstractmethod
    def matches(self, value: str | None) -> bool:
        """test the given value and return whether there is a match"""


class NullMatcher(Matcher):
    ORDER = 0

    def matches(self, value: str | None) -> bool:
        return value is None


class PatternMatcher(Matcher):
    ORDER = 2

    def __init__(self, pattern: str) -> None:
        self.pattern = re.compile(pattern)

    def matches(self, value: str | None) -> bool:
        if value is None:
            return False
        return self.pattern.match(value) is not None


class TimeMatcher(Matcher):
    ORDER = 0

    def __init__(self, value: datetime) -> None:
        self.value = value

    def matches(self, value: datetime) -> bool:  # type: ignore[override]
        return self.value == value


class TimeRangeMatcher(TimeMatcher):
    ORDER = 1

    def __init__(self, after: datetime | None, before: datetime | None) -> None:
        assert (
            after is not None or before is not None
        ), "at least one of 'after' and 'before' must be set"
        self.before = before
        self.after = after

    def matches(self, value: datetime) -> bool:  # type: ignore[override]
        if self.after is not None and value <= self.after:
            return False
        if self.before is not None and value >= self.before:
            return False
        return True


@dataclass
class ValueMatcher(Matcher):
    value: str
    ORDER = 1

    def matches(self, value: str | None) -> bool:
        if value is None:
            return False
        return value == self.value


# get the maximum ORDER value for any of the matches
MAX_MATCHER_ORDER = max(
    m.ORDER
    for name, m in inspect.getmembers(sys.modules[__name__])
    if inspect.isclass(m) and m is not Matcher and issubclass(m, Matcher)
)


class StringPropertySymptom(Symptom):
    ORDER = 0

    def __init__(self, obj: dict[str, Any]) -> None:
        super().__init__(obj)
        self.attr = obj["type"]
        self.matcher = Matcher.create(obj)

    def matches(self, report) -> bool:
        return self.matcher.matches(getattr(report, self.attr))


class URLSymptom(Symptom):
    ORDER = 1

    def __init__(self, obj: dict[str, Any]) -> None:
        super().__init__(obj)
        self.part = obj.get("part")
        self.matcher = Matcher.create(obj)

    def matches(self, report: Report) -> bool:
        LOG.debug("url: %r", report.url)
        if self.part is None:
            value = report.url.geturl()
            LOG.debug("matching against whole url: %s", value)
        else:
            value = getattr(report.url, self.part)
            if value is not None:
                value = str(value)
            LOG.debug("matching against url part %s: %s", self.part, value)
        return self.matcher.matches(value)


class ReportedAtSymptom(Symptom):
    ORDER = 2

    def __init__(self, obj: dict[str, Any]) -> None:
        super().__init__(obj)
        self.matcher = Matcher.create(obj)

    def matches(self, report: Report) -> bool:
        return self.matcher.matches(report.reported_at)  # type: ignore[arg-type]


class DetailsSymptom(Symptom):
    ORDER = 3

    def __init__(self, obj: dict[str, Any]) -> None:
        super().__init__(obj)
        if "path" in obj:
            self.path = jsonpath(obj["path"])
        else:
            self.path = None
        self.matcher = Matcher.create(obj)

    def matches(self, report: Report) -> bool:
        if self.path is None:
            return self.matcher.matches(json.dumps(report.details))
        # iterate over the jsonpath values
        return any(
            self.matcher.matches(value.value)
            for value in self.path.find(report.details)
            if value.value is None or isinstance(value.value, str)
        )
