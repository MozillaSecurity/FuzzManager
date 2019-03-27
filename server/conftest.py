# coding: utf-8
'''Common utilities for tests

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import logging
from django.apps import apps
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
import pytest
from rest_framework.test import APIClient

logging.getLogger("django").setLevel(logging.WARNING)
logging.basicConfig(level=logging.DEBUG)


LOG = logging.getLogger("fm.tests")


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def migration_hook(request):
    '''
    Pause migration at the migration named in @pytest.mark.migrate_from('0001-initial-migration')

    The migration_hook param will be a callable to then trigger the migration named in:
        @pytest.mark.migrate_from('0002-migrate-things')

    migration_hook also has an 'apps' attribute which is used to lookup models in the current migration state

    eg.
        MyModel = migration_hook.apps.get_model('myapp', 'MyModel')

    based on: https://www.caktusgroup.com/blog/2016/02/02/writing-unit-tests-django-migrations/
    '''

    migrate_from_mark = request.node.get_closest_marker('migrate_from')
    assert migrate_from_mark, 'must mark the migration to stop at with @pytest.mark.migrate_from()'
    assert len(migrate_from_mark.args) == 1, 'migrate_from mark expects 1 arg'
    assert not migrate_from_mark.kwargs, 'migrate_from mark takes no keywords'
    migrate_to_mark = request.node.get_closest_marker('migrate_to')
    assert migrate_to_mark, 'must mark the migration to hook with @pytest.mark.migrate_to()'
    assert len(migrate_to_mark.args) == 1, 'migrate_to mark expects 1 arg'
    assert not migrate_to_mark.kwargs, 'migrate_to mark takes no keywords'

    app = apps.get_containing_app_config(request.module.__name__).name

    migrate_from = [(app, migrate_from_mark.args[0])]
    migrate_to = [(app, migrate_to_mark.args[0])]

    class migration_hook_result(object):

        def __init__(self, _from, _to):
            self._to = _to
            executor = MigrationExecutor(connection)
            self.apps = executor.loader.project_state(_from).apps

            # Reverse to the original migration
            executor.migrate(_from)

        def __call__(self):
            # Run the migration to test
            executor = MigrationExecutor(connection)
            executor.loader.build_graph()  # reload.
            executor.migrate(self._to)

            self.apps = executor.loader.project_state(self._to).apps

    yield migration_hook_result(migrate_from, migrate_to)
