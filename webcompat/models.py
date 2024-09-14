# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import difflib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from logging import getLogger
from pathlib import Path
from typing import Any
from urllib.parse import SplitResult, urlsplit

from dateutil.parser import isoparse
from jsonschema import Draft202012Validator as Validator

from .symptoms import Symptom

LOG = getLogger(__file__)


def _load_schema() -> Validator:
    with (Path(__file__).parent / "schemas" / "signature.json").open() as schema_fd:
        schema = json.load(schema_fd)
    Validator.check_schema(schema)
    return Validator(schema)


SIG_SCHEMA = _load_schema()


@dataclass
class Report:
    """WebCompat report. It also supports generating a Signature based on the stored
    information.
    """

    app_name: str
    app_version: str
    comments: str
    # details is intentionally vague
    # .. this is a JSON blob in the report
    details: dict[str, dict[str, Any]]
    os: str
    reported_at: datetime
    uuid: str
    url: SplitResult
    app_channel: str | None = None
    breakage_category: str | None = None

    @classmethod
    def load(cls, data: str) -> "Report":
        result = json.loads(data)
        result["details"] = json.loads(result["details"])
        result["reported_at"] = isoparse(result["reported_at"]).replace(
            tzinfo=timezone.utc
        )
        result["url"] = urlsplit(result["url"])
        return cls(**result)

    def create_signature(self) -> "Signature":
        """Create a default signature"""
        return Signature(
            f"""
            {{
              "symptoms": [
                {{
                  "type": "url",
                  "part": "netloc",
                  "value": "{self.url.netloc}"
                }}
              ]
            }}
            """
        )


@dataclass
class Signature:
    raw_signature: str
    symptoms: list[Symptom] = field(default_factory=list)

    def __post_init__(self) -> None:
        try:
            data = json.loads(self.raw_signature)
        except ValueError as exc:
            raise RuntimeError(f"Invalid JSON: {exc}") from exc

        # raise any errors found by schema validation
        for error in SIG_SCHEMA.iter_errors(data):
            raise RuntimeError(error.message)

        # Get the symptoms objects (mandatory)
        for raw_symptom_obj in data["symptoms"]:
            self.symptoms.append(Symptom.load(raw_symptom_obj))

        self.symptoms.sort(key=Symptom.order)

    @classmethod
    def load(cls, data: str) -> "Signature":
        return cls(raw_signature=data)

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
        symptoms_diff = []
        for symptom in self.symptoms:
            if symptom.matches(report):
                symptoms_diff.append({"offending": False, "symptom": symptom})

        return symptoms_diff

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
