"""Common utilities for tests

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
import sys
from pathlib import Path


def pytest_ignore_collect(path, config):
    # Django 4.1 requires 3.8
    # 3.11 causes an ImportError in vine (via celery)
    if sys.version_info < (3, 8) or sys.version_info >= (3, 11):
        rel_path = Path(path).relative_to(config.rootdir)
        if rel_path.parts[0] in {
            "server",
            "Collector",
            "EC2Reporter",
            "TaskStatusReporter",
        }:
            return True
    return False
