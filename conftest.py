"""Common utilities for tests

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""

import contextlib
import importlib
import sys

# Currently, the version of django used here is not supported by python 3.12
# Check that django is available before setting the pytest_plugins otherwise the tests
# will fail.
if importlib.util.find_spec("django"):
    pytest_plugins = ["covmanager.tests.conftest"]

    with contextlib.suppress(ImportError):
        import pytest
        from django.core.cache import cache

        # Cache clearing ensures each test starts with fresh rate limit counters,
        # preventing false throttling errors and maintaining test isolation
        @pytest.fixture(autouse=True)
        def clear_cache():
            cache.clear()
            yield
            cache.clear()


def pytest_ignore_collect(collection_path, config):
    # 3.12 not supported yet
    if sys.version_info >= (3, 12):
        rel_path = collection_path.relative_to(config.rootdir)
        if rel_path.parts[0] in {
            "server",
            "Collector",
            "EC2Reporter",
            "TaskStatusReporter",
        }:
            return True
    return None
