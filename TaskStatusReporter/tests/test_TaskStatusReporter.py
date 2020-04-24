from __future__ import absolute_import

import pytest
from six.moves.urllib.parse import urlsplit

from TaskStatusReporter.TaskStatusReporter import TaskStatusReporter, main
from taskmanager.models import Task
from taskmanager.tests import create_pool, create_task

try:
    from unittest.mock import Mock, patch
except ImportError:
    from mock import Mock, patch


pytestmark = pytest.mark.django_db(transaction=True)
pytest_plugins = 'server.tests'


def test_taskstatusreporter_help(capsys):
    '''Test that help prints without throwing'''
    with pytest.raises(SystemExit):
        main()
    _, err = capsys.readouterr()
    assert err.startswith('usage: ')


#@pytest.mark.skipif(str is bytes, reason="TaskManager requires python3")
@patch('os.path.expanduser')
@patch('time.sleep', new=Mock())
def test_taskstatusreporter_report(mock_expanduser, live_server, tmp_path, fm_user):
    '''Test report submission'''
    mock_expanduser.side_effect = lambda path: str(tmp_path)  # ensure fuzzmanager config is not used

    # create a task
    pool = create_pool()
    host = create_task(pool=pool, task_id='abc', run_id=0)

    # create a reporter
    url = urlsplit(live_server.url)
    sigcache_path = tmp_path / 'sigcache'
    sigcache_path.mkdir()
    reporter = TaskStatusReporter(sigCacheDir=str(sigcache_path),
                                  serverHost=url.hostname,
                                  serverPort=url.port,
                                  serverProtocol=url.scheme,
                                  serverAuthToken=fm_user.token,
                                  clientId='task-abc-run-0')

    reporter.report('data')
    host = Task.objects.get(pk=host.pk)  # re-read
    assert host.status_data == 'data'

    reporter = TaskStatusReporter(sigCacheDir=str(sigcache_path),
                                  serverHost=url.hostname,
                                  serverPort=url.port,
                                  serverProtocol=url.scheme,
                                  serverAuthToken=fm_user.token,
                                  clientId='host2')

    with pytest.raises(RuntimeError, message="Server unexpectedly responded with status code 404: Not found"):
        reporter.report('data')
