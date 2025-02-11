"""
Tests

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
"""

import json
import os
import tempfile
from pathlib import Path

from CovReporter.CovReporter import CovReporter

FIXTURE_PATH = Path(__file__).parent / "fixtures"


def test_CovReporterCoverallsVersionData():
    coveralls_data = json.loads((FIXTURE_PATH / "coveralls_data.json").read_text())
    ret = CovReporter.version_info_from_coverage_data(coveralls_data)
    assert ret["revision"] == "1a0d9545b9805f50a70de703a3c04fc0d22e3839"
    assert ret["branch"] == "master"


def test_CovReporterPreprocessData():
    coveralls_data = json.loads((FIXTURE_PATH / "coveralls_data.json").read_text())
    result = CovReporter.preprocess_coverage_data(coveralls_data)

    children = "children"
    coverage = "coverage"
    name = "name"
    linesTotal = "linesTotal"
    linesMissed = "linesMissed"
    linesCovered = "linesCovered"
    coveragePercent = "coveragePercent"

    # Check that we have all the topdirs
    assert "topdir1" in result[children], "topdir1 missing in result"
    assert "topdir2" in result[children], "topdir2 missing in result"

    # Check that we have all the subdirs
    assert (
        "subdir1" in result[children]["topdir1"][children]
    ), "subdir1 missing in result"
    assert (
        "subdir2" in result[children]["topdir1"][children]
    ), "subdir2 missing in result"
    assert (
        "subdir1" in result[children]["topdir2"][children]
    ), "subdir1 missing in result"

    # Check that we haven't got more subdirs than expected for topdir2
    assert len(result[children]["topdir2"][children]) == 1

    # Check length of coverage list, name and summary values for file1.c
    assert (
        len(
            result[children]["topdir1"][children]["subdir1"][children]["file1.c"][
                coverage
            ]
        )
        == 9
    )
    assert (
        result[children]["topdir1"][children]["subdir1"][children]["file1.c"][name]
        == "file1.c"
    )
    assert (
        result[children]["topdir1"][children]["subdir1"][children]["file1.c"][
            linesTotal
        ]
        == 6
    )
    assert (
        result[children]["topdir1"][children]["subdir1"][children]["file1.c"][
            linesMissed
        ]
        == 2
    )
    assert (
        result[children]["topdir1"][children]["subdir1"][children]["file1.c"][
            linesCovered
        ]
        == 4
    )
    assert (
        result[children]["topdir1"][children]["subdir1"][children]["file1.c"][
            coveragePercent
        ]
        == 66.67
    )

    # Check name and summary values for topdir1/subdir1/
    assert result[children]["topdir1"][children]["subdir1"][name] == "subdir1"
    assert result[children]["topdir1"][children]["subdir1"][linesTotal] == 13
    assert result[children]["topdir1"][children]["subdir1"][linesCovered] == 10
    assert result[children]["topdir1"][children]["subdir1"][linesMissed] == 3
    assert result[children]["topdir1"][children]["subdir1"][coveragePercent] == 76.92

    # Check summary values for topdir1/subdir2/
    assert result[children]["topdir1"][children]["subdir2"][linesTotal] == 6
    assert result[children]["topdir1"][children]["subdir2"][linesCovered] == 4
    assert result[children]["topdir1"][children]["subdir2"][linesMissed] == 2

    # Check summary values for topdir1/
    assert result[children]["topdir1"][linesTotal] == 19
    assert result[children]["topdir1"][linesCovered] == 14
    assert result[children]["topdir1"][linesMissed] == 5

    # Check summary values for topdir2/
    assert result[children]["topdir2"][linesTotal] == 6
    assert result[children]["topdir2"][linesCovered] == 0
    assert result[children]["topdir2"][linesMissed] == 6
    assert result[children]["topdir2"][coveragePercent] == 0.0

    # Check that our converter replaces null with -1 to save some space
    assert (
        result[children]["topdir1"][children]["subdir1"][children]["file1.c"][coverage][
            0
        ]
        == -1
    )


def test_CovReporterMergeData():
    # result = CovReporter.preprocess_coverage_data(coverallsData)
    # result2 = CovReporter.preprocess_coverage_data(coverallsAddData)

    (cov_file1_fd, cov_file1) = tempfile.mkstemp(
        suffix=".cov", prefix="tmpTestCovReporter"
    )
    (cov_file2_fd, cov_file2) = tempfile.mkstemp(
        suffix=".cov", prefix="tmpTestCovReporter"
    )
    coveralls_data = json.loads((FIXTURE_PATH / "coveralls_data.json").read_text())
    coveralls_add_data = json.loads(
        (FIXTURE_PATH / "coveralls_add_data.json").read_text()
    )

    try:
        with os.fdopen(cov_file1_fd, "w") as f:
            json.dump(coveralls_data, f)

        with os.fdopen(cov_file2_fd, "w") as f:
            json.dump(coveralls_add_data, f)

        (result, version, stats) = CovReporter.create_combined_coverage(
            [cov_file1, cov_file2]
        )
    finally:
        os.remove(cov_file1)
        os.remove(cov_file2)

    assert version["revision"] == "1a0d9545b9805f50a70de703a3c04fc0d22e3839"
    assert version["branch"] == "master"

    children = "children"
    coverage = "coverage"
    name = "name"
    linesTotal = "linesTotal"
    linesMissed = "linesMissed"
    linesCovered = "linesCovered"
    coveragePercent = "coveragePercent"

    # Check that we have all the topdirs
    assert "topdir1" in result[children], "topdir1 missing in result"
    assert "topdir2" in result[children], "topdir2 missing in result"
    assert "topdir3" in result[children], "topdir2 missing in result"

    # Check that we have all the subdirs
    assert (
        "subdir1" in result[children]["topdir1"][children]
    ), "subdir1 missing in result"
    assert (
        "subdir2" in result[children]["topdir1"][children]
    ), "subdir2 missing in result"
    assert (
        "subdir1" in result[children]["topdir2"][children]
    ), "subdir1 missing in result"
    assert (
        "subdir3" in result[children]["topdir1"][children]
    ), "subdir3 missing in result"

    # Check that we haven't got more subdirs than expected for topdirs
    assert len(result[children]["topdir1"][children]) == 3
    assert len(result[children]["topdir2"][children]) == 1
    assert len(result[children]["topdir3"][children]) == 1

    # Check length of coverage list, name and summary values for file1.c
    assert (
        len(
            result[children]["topdir1"][children]["subdir1"][children]["file1.c"][
                coverage
            ]
        )
        == 9
    )
    assert (
        result[children]["topdir1"][children]["subdir1"][children]["file1.c"][name]
        == "file1.c"
    )
    assert (
        result[children]["topdir1"][children]["subdir1"][children]["file1.c"][
            linesTotal
        ]
        == 6
    )
    assert (
        result[children]["topdir1"][children]["subdir1"][children]["file1.c"][
            linesMissed
        ]
        == 1
    )
    assert (
        result[children]["topdir1"][children]["subdir1"][children]["file1.c"][
            linesCovered
        ]
        == 5
    )
    assert (
        result[children]["topdir1"][children]["subdir1"][children]["file1.c"][
            coveragePercent
        ]
        == 83.33
    )

    # Check updated counters in file1.c
    assert (
        result[children]["topdir1"][children]["subdir1"][children]["file1.c"][coverage][
            2
        ]
        == 18
    )
    assert (
        result[children]["topdir1"][children]["subdir1"][children]["file1.c"][coverage][
            3
        ]
        == 12
    )
    assert (
        result[children]["topdir1"][children]["subdir1"][children]["file1.c"][coverage][
            7
        ]
        == 2
    )

    # Check name and summary values for topdir1/subdir1/
    assert result[children]["topdir1"][children]["subdir1"][name] == "subdir1"
    assert result[children]["topdir1"][children]["subdir1"][linesTotal] == 13
    assert result[children]["topdir1"][children]["subdir1"][linesCovered] == 11
    assert result[children]["topdir1"][children]["subdir1"][linesMissed] == 2
    assert result[children]["topdir1"][children]["subdir1"][coveragePercent] == 84.62

    # Check summary values for topdir1/subdir2/
    assert result[children]["topdir1"][children]["subdir2"][linesTotal] == 6
    assert result[children]["topdir1"][children]["subdir2"][linesCovered] == 4
    assert result[children]["topdir1"][children]["subdir2"][linesMissed] == 2

    # Check summary values for topdir1/
    assert result[children]["topdir1"][linesTotal] == 25
    assert result[children]["topdir1"][linesCovered] == 18
    assert result[children]["topdir1"][linesMissed] == 7

    # Check summary values for topdir2/
    assert result[children]["topdir2"][linesTotal] == 6
    assert result[children]["topdir2"][linesCovered] == 0
    assert result[children]["topdir2"][linesMissed] == 6
    assert result[children]["topdir2"][coveragePercent] == 0.0

    # Check summary values for topdir2/
    assert result[children]["topdir3"][linesTotal] == 6
    assert result[children]["topdir3"][linesCovered] == 6
    assert result[children]["topdir3"][linesMissed] == 0
    assert result[children]["topdir3"][coveragePercent] == 100.0

    # Check that our converter replaces null with -1 to save some space
    assert (
        result[children]["topdir1"][children]["subdir1"][children]["file1.c"][coverage][
            0
        ]
        == -1
    )
