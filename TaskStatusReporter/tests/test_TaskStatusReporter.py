from unittest.mock import Mock, patch
from urllib.parse import urlsplit

import pytest

from Reporter.Reporter import ServerError
from taskmanager.models import Task
from taskmanager.tests import create_pool, create_task
from TaskStatusReporter.TaskStatusReporter import TaskStatusReporter, main

pytestmark = pytest.mark.django_db(transaction=True)
pytest_plugins = "server.tests"


def test_taskstatusreporter_help(capsys):
    """Test that help prints without throwing"""
    with pytest.raises(SystemExit):
        main()
    _, err = capsys.readouterr()
    assert err.startswith("usage: ")


# @pytest.mark.skipif(str is bytes, reason="TaskManager requires python3")
@patch("os.path.expanduser")
@patch("time.sleep", new=Mock())
def test_taskstatusreporter_report(mock_expanduser, live_server, tmp_path, fm_user):
    """Test report submission"""
    mock_expanduser.side_effect = lambda path: str(
        tmp_path
    )  # ensure fuzzmanager config is not used

    # create a task
    pool = create_pool()
    host = create_task(pool=pool, task_id="abc", run_id=0)

    # create a reporter
    url = urlsplit(live_server.url)
    sigcache_path = tmp_path / "sigcache"
    sigcache_path.mkdir()
    reporter = TaskStatusReporter(
        sigCacheDir=str(sigcache_path),
        serverHost=url.hostname,
        serverPort=url.port,
        serverProtocol=url.scheme,
        serverAuthToken=fm_user.token,
        clientId="task-abc-run-0",
    )

    reporter.report("data")
    host = Task.objects.get(pk=host.pk)  # re-read
    assert host.status_data == "data"

    reporter = TaskStatusReporter(
        sigCacheDir=str(sigcache_path),
        serverHost=url.hostname,
        serverPort=url.port,
        serverProtocol=url.scheme,
        serverAuthToken=fm_user.token,
        clientId="host2",
    )

    with pytest.raises(ServerError) as exc:
        reporter.report("data")
    assert "Server unexpectedly responded with status code 404:" in str(exc.value)
