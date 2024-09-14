import json
from urllib.parse import urlsplit

import pytest

from webcompat.models import Report, Signature
from webcompat.symptoms import (
    DetailsSymptom,
    NullMatcher,
    PatternMatcher,
    ReportedAtSymptom,
    StringPropertySymptom,
    TimeMatcher,
    TimeRangeMatcher,
    URLSymptom,
    ValueMatcher,
)


def test_report_01():
    """test basic Report load and default signature create/match"""
    report = Report.load(
        json.dumps(
            {
                "app_channel": "C",
                "app_name": "N",
                "app_version": "V",
                "breakage_category": "B",
                "comments": "",
                "details": "{}",
                "os": "O",
                "reported_at": "1999-01-01T12:00:00",
                "url": "s://d.x/",
                "uuid": "dd909949-f9fe-4a4a-b934-9d041e7f0117",
            }
        )
    )
    sig = report.create_signature()
    assert sig.matches(report)


@pytest.mark.parametrize(
    "field",
    (
        "app_channel",
        "app_name",
        "app_version",
        "breakage_category",
        "comments",
        "os",
        "uuid",
    ),
)
@pytest.mark.parametrize("match", ("pattern", "value"))
def test_signature_01(field, match):
    """test regular string matching fields"""
    report = Report.load(
        json.dumps(
            {
                "app_channel": "app_channel_v",
                "app_name": "app_name_v",
                "app_version": "app_version_v",
                "breakage_category": "breakage_category_v",
                "comments": "comments_v",
                "details": '"details_v"',
                "os": "os_v",
                "reported_at": "1999-01-01T12:00:00",
                "url": "url_v",
                "uuid": "uuid_v",
            }
        )
    )

    signature = Signature(
        f"""
        {{
          "symptoms": [
            {{
              "type": "{field}",
              "{match}": "{field}_v"
            }}
          ]
        }}
        """
    )
    assert signature.matches(report)

    setattr(report, field, None)
    assert not signature.matches(report)


def test_signature_02():
    report = Report.load(
        json.dumps(
            {
                "app_channel": "C",
                "app_name": "N",
                "app_version": "V",
                "breakage_category": "B",
                "comments": "",
                "details": "{}",
                "os": "O",
                "reported_at": "1999-01-01T12:00:00",
                "url": "s://d.x/",
                "uuid": "dd909949-f9fe-4a4a-b934-9d041e7f0117",
            }
        )
    )

    signature = Signature(
        """
        {
          "symptoms": [
            {
              "type": "app_channel",
              "value": null
            }
          ]
        }
        """
    )
    assert not signature.matches(report)

    report.app_channel = None
    assert signature.matches(report)


@pytest.mark.parametrize(
    "field,value,good,bad",
    (
        ("fragment", "f", "s://h/#f", "s://h/#bad"),
        ("hostname", "h", "s://h/", "s://bad/"),
        ("netloc", "u@h:1337", "s://u@h:1337/", "s://bad@h:1337/"),
        ("netloc", "u@h:1337", None, "s://u@bad:1337/"),
        ("netloc", "u@h:1337", None, "s://u@h:666/"),
        ("password", "p", "s://u:p@h/", "s://u:bad@h/"),
        ("path", "/p", "s://h/p", "s://h/bad"),
        ("port", "1337", "s://h:1337/", "s://h:666/"),
        ("query", "q", "s://h/?q", "s://h/?bad"),
        ("scheme", "s", "s://h", "bad://h"),
        ("username", "u", "s://u@h/", "s://bad@h/"),
    ),
)
@pytest.mark.parametrize("match", ("pattern", "value"))
def test_signature_03(bad, field, good, match, value):
    """test url part matching"""
    report = Report.load(
        json.dumps(
            {
                "app_channel": "C",
                "app_name": "N",
                "app_version": "V",
                "breakage_category": "B",
                "comments": "R",
                "details": '"D"',
                "os": "S",
                "reported_at": "1999-01-01T12:00:00",
                "url": good,
                "uuid": "U",
            }
        )
    )

    signature = Signature(
        f"""
        {{
          "symptoms": [
            {{
              "type": "url",
              "part": "{field}",
              "{match}": "{value}"
            }}
          ]
        }}
        """
    )
    if good is not None:
        assert signature.matches(report)

    report.url = urlsplit(bad)
    assert not signature.matches(report)


@pytest.mark.parametrize("match", ("pattern", "value"))
def test_signature_04(match):
    """test whole url matching"""
    report = Report.load(
        json.dumps(
            {
                "app_channel": "C",
                "app_name": "N",
                "app_version": "V",
                "breakage_category": "B",
                "comments": "R",
                "details": '"D"',
                "os": "S",
                "reported_at": "1999-01-01T12:00:00",
                "url": "s://h/p",
                "uuid": "U",
            }
        )
    )

    signature = Signature(
        f"""
        {{
          "symptoms": [
            {{
              "type": "url",
              "{match}": "s://h/p"
            }}
          ]
        }}
        """
    )
    assert signature.matches(report)

    report.url = urlsplit("s://h/bad")
    assert not signature.matches(report)


@pytest.mark.parametrize(
    "rules,reported,result",
    (
        ('"after":"1999-01-01","before":"1999-12-31",', "1999-06-01", True),
        ('"after":"1999-01-01",', "1998-12-31", False),
        ('"before":"1999-12-31",', "2000-01-01", False),
        ('"time":"1999-12-31",', "1999-12-30", False),
        ('"time":"1999-12-31",', "1999-12-31", True),
        ('"time":"1999-12-31",', "2000-01-01", False),
    ),
)
def test_signature_05(reported, result, rules):
    """test reported_at matching"""
    report = Report.load(
        json.dumps(
            {
                "app_channel": "C",
                "app_name": "N",
                "app_version": "V",
                "breakage_category": "B",
                "comments": "R",
                "details": '"D"',
                "os": "S",
                "reported_at": reported,
                "url": "s://h/p",
                "uuid": "U",
            }
        )
    )
    signature = Signature(
        f"""
        {{
          "symptoms": [
            {{
              {rules}
              "type": "reported_at"
            }}
          ]
        }}
        """
    )
    assert signature.matches(report) is result


@pytest.mark.parametrize("path,result", (("$.bi.env", True), ("$", False)))
@pytest.mark.parametrize("match", ("pattern", "value"))
def test_signature_06(match, path, result):
    """test details path matching"""
    report = Report.load(
        json.dumps(
            {
                "app_channel": "C",
                "app_name": "N",
                "app_version": "V",
                "breakage_category": "B",
                "comments": "R",
                "details": '{ "bi": {"env": "var"} }',
                "os": "S",
                "reported_at": "1999-01-01T12:00:00",
                "url": "s://h/p",
                "uuid": "U",
            }
        )
    )
    signature = Signature(
        f"""
        {{
          "symptoms": [
            {{
              "type": "details",
              "path": "{path}",
              "{match}": "var"
            }}
          ]
        }}
        """
    )
    assert signature.matches(report) is result


@pytest.mark.parametrize("match,result", (("pattern", True), ("value", False)))
def test_signature_07(match, result):
    """test details non-path matching"""
    report = Report.load(
        json.dumps(
            {
                "app_channel": "C",
                "app_name": "N",
                "app_version": "V",
                "breakage_category": "B",
                "comments": "R",
                "details": '{ "bi": {"env": "var"} }',
                "os": "S",
                "reported_at": "1999-01-01T12:00:00",
                "url": "s://h/p",
                "uuid": "U",
            }
        )
    )
    signature = Signature(
        f"""
        {{
          "symptoms": [
            {{
              "type": "details",
              "{match}": ".*var.*"
            }}
          ]
        }}
        """
    )
    assert signature.matches(report) is result


def test_signature_08():
    """test symptom ordering"""
    sig = Signature(
        """
        {
          "symptoms": [
            {"type": "reported_at", "after": "1999"},
            {"type": "reported_at", "time": "1999"},
            {"type": "details", "value": null},
            {"type": "details", "pattern": ""},
            {"type": "details", "value": ""},
            {"type": "url", "part": "scheme", "value": null},
            {"type": "url", "part": "scheme", "pattern": ""},
            {"type": "url", "part": "scheme", "value": ""},
            {"type": "os", "value": ""},
            {"type": "os", "pattern": ""},
            {"type": "os", "value": null}
          ]
        }
        """
    )
    assert isinstance(sig.symptoms[0], StringPropertySymptom)
    assert isinstance(sig.symptoms[0].matcher, NullMatcher)
    assert isinstance(sig.symptoms[1], StringPropertySymptom)
    assert isinstance(sig.symptoms[1].matcher, ValueMatcher)
    assert isinstance(sig.symptoms[2], StringPropertySymptom)
    assert isinstance(sig.symptoms[2].matcher, PatternMatcher)
    assert isinstance(sig.symptoms[3], URLSymptom)
    assert isinstance(sig.symptoms[3].matcher, NullMatcher)
    assert isinstance(sig.symptoms[4], URLSymptom)
    assert isinstance(sig.symptoms[4].matcher, ValueMatcher)
    assert isinstance(sig.symptoms[5], URLSymptom)
    assert isinstance(sig.symptoms[5].matcher, PatternMatcher)
    assert isinstance(sig.symptoms[6], ReportedAtSymptom)
    assert isinstance(sig.symptoms[6].matcher, TimeMatcher)
    assert isinstance(sig.symptoms[7], ReportedAtSymptom)
    assert isinstance(sig.symptoms[7].matcher, TimeRangeMatcher)
    assert isinstance(sig.symptoms[8], DetailsSymptom)
    assert isinstance(sig.symptoms[8].matcher, NullMatcher)
    assert isinstance(sig.symptoms[9], DetailsSymptom)
    assert isinstance(sig.symptoms[9].matcher, ValueMatcher)
    assert isinstance(sig.symptoms[10], DetailsSymptom)
    assert isinstance(sig.symptoms[10].matcher, PatternMatcher)
