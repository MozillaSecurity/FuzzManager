"""Common utilities for tests

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
import sys


def pytest_ignore_collect(collection_path, config):
    # 3.12 not supported yet
    if sys.version_info >= (3, 12):
        rel_path = collection_path.relative_to(config.rootdir)
        if rel_path.parts[0] == "server":
            return True
    return None
