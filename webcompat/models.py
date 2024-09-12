# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import difflib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import ParseResult, urlparse
from uuid import UUID

from dateutil.parser import isoparse
from jsonschema.protocols import Validator

from .symptoms import Symptom


def _load_schema() -> Validator:
    with (Path(__file__).parent / "schemas" / "signature.json").open() as schema_fd:
        schema = json.load(schema_fd)
    Validator.check_schema(schema)
    return Validator(schema)


SIG_SCHEMA = _load_schema()


@dataclass
class Report:
    app_channel: str | None
    app_name: str
    app_version: str
    breakage_category: str
    comments: str
    # details is intentionally vague
    # .. this is a JSON blob in the report
    details: dict[str, dict[str, Any]]
    os: str
    reported_at: datetime
    url: ParseResult
    uuid: UUID

    @classmethod
    def load(cls, data: str) -> "Report":
        result = json.loads(data)
        result["details"] = json.loads(result["details"])
        result["uuid"] = UUID(result["uuid"])
        result["reported_at"] = isoparse(result["reported_at"])
        result["url"] = urlparse(result["url"])
        return cls(**result)


@dataclass(init=False)
class Signature:
    raw_signature: str
    symptoms: list[Symptom]

    def __init__(self, raw_signature: str) -> None:
        # For now, we store the original raw signature and hand it out for
        # conversion to String. This is fine as long as our Signature object
        # is immutable. Later, we should implement a method that actually
        # serializes this object back to JSON as it is.
        self.raw_signature = raw_signature
        self.symptoms = []

        try:
            obj = json.loads(raw_signature)
        except ValueError as exc:
            raise RuntimeError(f"Invalid JSON: {exc}") from exc

        # raise any errors found by schema validation
        for error in SIG_SCHEMA.iter_errors(obj):
            raise RuntimeError(error.message)

        # Get the symptoms objects (mandatory)
        for raw_symptom_obj in obj["symptoms"]:
            self.symptoms.append(Symptom.load(raw_symptom_obj))

        self.symptoms.sort(key=Symptom.order)

    @classmethod
    def load(cls, signature_file) -> "Signature":
        with open(signature_file) as sig_fd:
            return cls(sig_fd.read())

    def __str__(self) -> str:
        return json.dumps({"symptoms": self.symptoms}, indent=2, sort_keys=True)

    def matches(self, report: Report) -> bool:
        """
        Match this signature against the given report information

        @type reportInfo: ReportInfo
        @param reportInfo: The report info to match the signature against

        @rtype: bool
        @return: True if the signature matches, False otherwise
        """
        return all(symptom.matches(report) for symptom in self.symptoms)

    def get_distance(self, report):
        distance = 0

        for symptom in self.symptoms:
            if not symptom.matches(report):
                distance += 1

        return distance

    def fit(self, report):
        sig_obj = {}
        sig_symptoms = []

        sig_obj["symptoms"] = sig_symptoms

        symptoms_diff = self.get_symptoms_diff(report)

        for symptom_diff in symptoms_diff:
            if symptom_diff["offending"]:
                if "proposed" in symptom_diff:
                    sig_symptoms.append(symptom_diff["proposed"].jsonobj)
            else:
                sig_symptoms.append(symptom_diff["symptom"].jsonobj)

        if not sig_symptoms:
            return None

        return Signature(json.dumps(sig_obj))

    def get_symptoms_diff(self, report):
        symptomsDiff = []
        for symptom in self.symptoms:
            if symptom.matches(report):
                symptomsDiff.append({"offending": False, "symptom": symptom})

        return symptomsDiff

    def get_signature_unified_diff_tuples(self, report):
        diff_tuples = []

        # the format here must match what is returned by `fit()`
        old_lines = str(self).splitlines()
        new_raw_report_signature = self.fit(report)
        if new_raw_report_signature:
            new_lines = str(new_raw_report_signature).splitlines()
        else:
            new_lines = []
        context = max(len(old_lines), len(new_lines))

        signature_diff = difflib.unified_diff(old_lines, new_lines, n=context)

        for diff_line in signature_diff:
            if (
                diff_line.startswith("+++")
                or diff_line.startswith("---")
                or diff_line.startswith("@@")
                or not diff_line.strip()
            ):
                continue

            diff_tuples.append((diff_line[0], diff_line[1:]))

        return diff_tuples
