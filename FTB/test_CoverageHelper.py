'''
Tests

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''
import json
import unittest
from FTB import CoverageHelper


covdata = r"""
{
  "children": {
    "topdir1": {
      "children": {
        "subdir1": {
          "children": {
            "file1.c": {
              "coverage": [
                -1,
                -1,
                12,
                12,
                10,
                2,
                0,
                0,
                -1
              ],
              "coveragePercent": 66.67,
              "linesCovered": 4,
              "linesMissed": 2,
              "linesTotal": 6,
              "name": "file1.c"
            },
            "file2.c": {
              "coverage": [
                -1,
                20,
                20,
                15,
                15,
                15,
                15,
                0,
                -1,
                -1
              ],
              "coveragePercent": 85.71,
              "linesCovered": 6,
              "linesMissed": 1,
              "linesTotal": 7,
              "name": "file2.c"
            }
          },
          "coveragePercent": 76.92,
          "linesCovered": 10,
          "linesMissed": 3,
          "linesTotal": 13,
          "name": "subdir1"
        },
        "subdir2": {
          "children": {
            "file3.c": {
              "coverage": [
                -1,
                -1,
                12,
                12,
                10,
                2,
                0,
                0,
                -1
              ],
              "coveragePercent": 66.67,
              "linesCovered": 4,
              "linesMissed": 2,
              "linesTotal": 6,
              "name": "file3.c"
            }
          },
          "coveragePercent": 66.67,
          "linesCovered": 4,
          "linesMissed": 2,
          "linesTotal": 6,
          "name": "subdir2"
        }
      },
      "coveragePercent": 73.68,
      "linesCovered": 14,
      "linesMissed": 5,
      "linesTotal": 19,
      "name": "topdir1"
    },
    "topdir2": {
      "children": {
        "subdir1": {
          "children": {
            "file1.c": {
              "coverage": [
                -1,
                -1,
                0,
                0,
                0,
                0,
                0,
                0,
                -1
              ],
              "coveragePercent": 0.0,
              "linesCovered": 0,
              "linesMissed": 6,
              "linesTotal": 6,
              "name": "file1.c"
            }
          },
          "coveragePercent": 0.0,
          "linesCovered": 0,
          "linesMissed": 6,
          "linesTotal": 6,
          "name": "subdir1"
        }
      },
      "coveragePercent": 0.0,
      "linesCovered": 0,
      "linesMissed": 6,
      "linesTotal": 6,
      "name": "topdir2"
    }
  },
  "coveragePercent": 56.0,
  "linesCovered": 14,
  "linesMissed": 11,
  "linesTotal": 25,
  "name": null
}
"""  # noqa


class TestCoverageHelperFlattenNames(unittest.TestCase):
    def runTest(self):
        node = json.loads(covdata)
        result = CoverageHelper.get_flattened_names(node, prefix="")

        expected_names = [
            'topdir1',
            'topdir1/subdir2',
            'topdir1/subdir2/file3.c',
            'topdir1/subdir1/file2.c',
            'topdir1/subdir1',
            'topdir1/subdir1/file1.c',
            'topdir2',
            'topdir2/subdir1',
            'topdir2/subdir1/file1.c'
        ]

        self.assertEqual(result, set(expected_names))


class TestCoverageHelperApplyDirectivesMixed(unittest.TestCase):
    def runTest(self):
        node = json.loads(covdata)

        # Check that mixed directives work properly (exclude multiple paths, include some back)
        directives = ["-:topdir1/subdir1/**",
                      "+:topdir1/subdir?/file1.c",
                      "+:topdir1/subdir?/file3.c",
                      "-:topdir1/subdir2/**"]

        CoverageHelper.apply_include_exclude_directives(node, directives)

        result = CoverageHelper.get_flattened_names(node, prefix="")

        expected_names = [
            'topdir1',
            'topdir1/subdir1/file1.c',
            'topdir1/subdir1',
            'topdir2',
            'topdir2/subdir1',
            'topdir2/subdir1/file1.c'
        ]

        self.assertEqual(result, set(expected_names))


class TestCoverageHelperApplyDirectivesPrune(unittest.TestCase):
    def runTest(self):
        node = json.loads(covdata)

        # Check that any empty childs are pruned (empty childs are not useful)
        directives = ["-:topdir1/subdir1/**", "-:topdir1/subdir2/**"]

        CoverageHelper.apply_include_exclude_directives(node, directives)

        result = CoverageHelper.get_flattened_names(node, prefix="")

        expected_names = [
            'topdir2',
            'topdir2/subdir1',
            'topdir2/subdir1/file1.c'
        ]

        self.assertEqual(result, set(expected_names))


class TestCoverageHelperApplyDirectivesExcludeAll(unittest.TestCase):
    def runTest(self):
        node = json.loads(covdata)

        # Check that excluding all paths works (specialized case)
        directives = ["-:**", "+:topdir2/subdir1/**"]

        CoverageHelper.apply_include_exclude_directives(node, directives)

        result = CoverageHelper.get_flattened_names(node, prefix="")

        expected_names = [
            'topdir2',
            'topdir2/subdir1',
            'topdir2/subdir1/file1.c'
        ]

        self.assertEqual(result, set(expected_names))


class TestCoverageHelperApplyDirectivesMakeEmpty(unittest.TestCase):
    def runTest(self):
        node = json.loads(covdata)

        # Check that making the set entirely empty doesn't crash things (tsmith mode)
        directives = ["-:**"]

        CoverageHelper.apply_include_exclude_directives(node, directives)

        result = CoverageHelper.get_flattened_names(node, prefix="")

        expected_names = []

        self.assertEqual(result, set(expected_names))


if __name__ == "__main__":
    unittest.main()
