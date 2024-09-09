"""Common utilities for tests

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
import importlib
import sys
from pathlib import Path

# Currently, the version of django used here is not supported by python 3.12
# Check that django is available before setting the pytest_plugins otherwise the tests
# will fail.
if importlib.util.find_spec("django"):
    pytest_plugins = ["covmanager.tests.conftest"]


def pytest_ignore_collect(path, config):
    # 3.12 not supported yet
    if sys.version_info >= (3, 12):
        rel_path = Path(path).relative_to(config.rootdir)
        if rel_path.parts[0] in {
            "server",
            "Collector",
            "TaskStatusReporter",
        }:
            return True
    return None
