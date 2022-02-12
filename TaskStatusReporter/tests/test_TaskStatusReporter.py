from __future__ import annotations

from pathlib import Path
from platform import libc_ver
from unittest.mock import Mock, patch

from django.contrib.auth.models import User
import pytest
from pytest_django.live_server_helper import LiveServer
from six.moves.urllib.parse import urlsplit

from TaskStatusReporter.TaskStatusReporter import TaskStatusReporter, main
from taskmanager.models import Task
from taskmanager.tests import create_pool, create_task


pytestmark = pytest.mark.django_db(transaction=True)
pytest_plugins = 'server.tests'


def test_taskstatusreporter_help(capsys: pytest.CaptureFixture[str]) -> None:
    '''Test that help prints without throwing'''
    with pytest.raises(SystemExit):
        main()
    _, err = capsys.readouterr()
    assert err.startswith('usage: ')


#@pytest.mark.skipif(str is bytes, reason="TaskManager requires python3")
@patch('os.path.expanduser')
@patch('time.sleep', new=Mock())
def test_taskstatusreporter_report(mock_expanduser: Mock, live_server: LiveServer, tmp_path: Path, fm_user: User) -> None:
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

    with pytest.raises(RuntimeError, match="Server unexpectedly responded with status code 404: Not found"):
        reporter.report('data')
