# coding: utf-8
'''
Tests

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''
from __future__ import absolute_import, unicode_literals
import json
import os
import platform
import zipfile

import pytest
import requests
from six.moves.urllib.parse import urlsplit

from Collector.Collector import Collector, main
from FTB.Signatures.CrashInfo import CrashInfo
from FTB.ProgramConfiguration import ProgramConfiguration
from crashmanager.models import CrashEntry

try:
    from unittest.mock import Mock, patch
except ImportError:
    from mock import Mock, patch


asanTraceCrash = '''ASAN:SIGSEGV
=================================================================
==5854==ERROR: AddressSanitizer: SEGV on unknown address 0x00000014 (pc 0x0810845f sp 0xffc57860 bp 0xffc57f18 T0)
    #0 0x810845e in js::AbstractFramePtr::asRematerializedFrame() const /srv/repos/mozilla-central/js/src/shell/../jit/RematerializedFrame.h:114
    #1 0x810845e in js::AbstractFramePtr::script() const /srv/repos/mozilla-central/js/src/shell/../vm/Stack-inl.h:572
    #2 0x810845e in EvalInFrame(JSContext*, unsigned int, JS::Value*) /srv/repos/mozilla-central/js/src/shell/js.cpp:2655
    #3 0x93f5b92 in js::CallJSNative(JSContext*, bool (*)(JSContext*, unsigned int, JS::Value*), JS::CallArgs const&) /srv/repos/mozilla-central/js/src/jscntxtinlines.h:231
    #4 0x93f5b92 in js::Invoke(JSContext*, JS::CallArgs, js::MaybeConstruct) /srv/repos/mozilla-central/js/src/vm/Interpreter.cpp:484
    #5 0x9346ba7 in js::Invoke(JSContext*, JS::Value const&, JS::Value const&, unsigned int, JS::Value const*, JS::MutableHandle<JS::Value>) /srv/repos/mozilla-central/js/src/vm/Interpreter.cpp:540
    #6 0x8702baa in js::jit::DoCallFallback(JSContext*, js::jit::BaselineFrame*, js::jit::ICCall_Fallback*, unsigned int, JS::Value*, JS::MutableHandle<JS::Value>) /srv/repos/mozilla-central/js/src/jit/BaselineIC.cpp:8638

AddressSanitizer can not provide additional info.
SUMMARY: AddressSanitizer: SEGV /srv/repos/mozilla-central/js/src/shell/../jit/RematerializedFrame.h:114 js::AbstractFramePtr::asRematerializedFrame() const
==5854==ABORTING'''  # noqa

exampleTestCase = b'''function init() {
    while ( {}, this) !(Object === "Infinity");
}
eval("init()");'''

pytestmark = pytest.mark.django_db(transaction=True)
pytest_plugins = ('server.tests',)


def test_collector_help(capsys):
    '''Test that help prints without throwing'''
    with pytest.raises(SystemExit):
        main()
    _, err = capsys.readouterr()
    assert err.startswith('usage: ')


@patch('os.path.expanduser')
@patch('time.sleep', new=Mock())
def test_collector_submit(mock_expanduser, live_server, tmp_path, fm_user):
    '''Test crash submission'''
    mock_expanduser.side_effect = lambda path: str(tmp_path)  # ensure fuzzmanager config is not used

    # create a collector
    url = urlsplit(live_server.url)
    (tmp_path / "sigcache").mkdir()
    collector = Collector(sigCacheDir=str(tmp_path / 'sigcache'),
                          serverHost=url.hostname,
                          serverPort=url.port,
                          serverProtocol=url.scheme,
                          serverAuthToken=fm_user.token,
                          clientId='test-fuzzer1',
                          tool='test-tool')
    (tmp_path / "testcase").mkdir()
    testcase_path = tmp_path / 'testcase' / 'testcase.js'
    with testcase_path.open('wb') as testcase_fp:
        testcase_fp.write(exampleTestCase)
    config = ProgramConfiguration('mozilla-central', 'x86-64', 'linux', version='ba0bc4f26681')
    crashInfo = CrashInfo.fromRawCrashData([], asanTraceCrash.splitlines(), config)

    # submit a crash to test server using collector
    result = collector.submit(crashInfo, str(testcase_path))

    # see that the issue was created in the server
    entry = CrashEntry.objects.get(pk=result['id'])
    assert entry.rawStdout == ''
    assert entry.rawStderr == asanTraceCrash
    assert entry.rawCrashData == ''
    assert entry.tool.name == 'test-tool'
    assert entry.client.name == 'test-fuzzer1'
    assert entry.product.name == config.product
    assert entry.product.version == config.version
    assert entry.platform.name == config.platform
    assert entry.os.name == config.os
    assert entry.testcase.quality == 0
    assert not entry.testcase.isBinary
    assert entry.testcase.size == len(exampleTestCase)
    with open(entry.testcase.test.path, 'rb') as testcase_fp:
        assert testcase_fp.read() == exampleTestCase
    assert entry.metadata == ''
    assert entry.env == ''
    assert entry.args == ''

    # create a test config
    with (tmp_path / ".fuzzmanagerconf").open("w") as fp:
        fp.write('[Main]\n')
        fp.write('serverhost = %s\n' % url.hostname)
        fp.write('serverport = %d\n' % url.port)
        fp.write('serverproto = %s\n' % url.scheme)
        fp.write('serverauthtoken = %s\n' % fm_user.token)

    # try a binary testcase via cmd line
    testcase_path = tmp_path / 'testcase.bin'
    with testcase_path.open('wb') as testcase_fp:
        testcase_fp.write(b'\0')
    stdout_path = tmp_path / 'stdout.txt'
    with stdout_path.open('w') as fp:
        fp.write('stdout data')
    stderr_path = tmp_path / 'stderr.txt'
    with stderr_path.open('w') as fp:
        fp.write('stderr data')
    crashdata_path = tmp_path / 'crashdata.txt'
    with crashdata_path.open('w') as fp:
        fp.write(asanTraceCrash)
    result = main([
        '--submit',
        '--tool', 'tool2',
        '--product', 'mozilla-inbound',
        '--productversion', '12345',
        '--os', 'minix',
        '--platform', 'pdp11',
        '--env', 'PATH=/home/ken', 'LD_PRELOAD=hack.so',
        '--metadata', 'var1=val1', 'var2=val2',
        '--args', './myprog',
        '--testcase', str(testcase_path),
        '--testcasequality', '5',
        '--stdout', str(stdout_path),
        '--stderr', str(stderr_path),
        '--crashdata', str(crashdata_path),
    ])
    assert result == 0
    entry = CrashEntry.objects.get(pk__gt=entry.id)  # newer than the last result, will fail if the test db is active
    assert entry.rawStdout == 'stdout data'
    assert entry.rawStderr == 'stderr data'
    assert entry.rawCrashData == asanTraceCrash
    assert entry.tool.name == 'tool2'
    assert entry.client.name == platform.node()
    assert entry.product.name == 'mozilla-inbound'
    assert entry.product.version == '12345'
    assert entry.platform.name == 'pdp11'
    assert entry.os.name == 'minix'
    assert entry.testcase.quality == 5
    assert entry.testcase.isBinary
    assert entry.testcase.size == 1
    with open(entry.testcase.test.path, 'rb') as testcase_fp:
        assert testcase_fp.read() == b'\0'
    assert json.loads(entry.metadata) == {'var1': 'val1', 'var2': 'val2'}
    assert json.loads(entry.env) == {'PATH': '/home/ken', 'LD_PRELOAD': 'hack.so'}
    assert json.loads(entry.args) == ['./myprog']

    class response_t(object):
        status_code = 500
        text = "Error"
    collector._session.post = lambda *_, **__: response_t()

    with pytest.raises(RuntimeError, match='Server unexpectedly responded'):
        collector.submit(crashInfo, str(testcase_path))


def test_collector_refresh(capsys, tmp_path):
    '''Test signature downloads'''
    # create a test signature zip
    test2_path = tmp_path / 'test2.signature'
    with test2_path.open('w') as fp:
        fp.write('test2')
    outzip_path = tmp_path / "out.zip"
    with zipfile.ZipFile(str(outzip_path), 'w') as zf:
        zf.write(str(test2_path), 'test2.signature')

    # create an old signature
    sigs_path = tmp_path / 'sigs'
    sigs_path.mkdir()
    (sigs_path / 'test1.signature').touch()
    (sigs_path / 'other.txt').touch()
    assert {f.name for f in sigs_path.iterdir()} == {'test1.signature', 'other.txt'}

    with outzip_path.open('rb') as fp:
        class response_t(object):
            status_code = requests.codes["ok"]
            text = "OK"
            raw = fp

        # this asserts the expected arguments and returns the open handle to out.zip as 'raw' which is read by refresh()
        def myget(url, stream=None, headers=None):
            assert url == 'gopher://aol.com:70/crashmanager/rest/signatures/download/'
            assert stream is True
            assert headers == {'Authorization': 'Token token'}
            return response_t()

        # create Collector
        collector = Collector(sigCacheDir=str(sigs_path),
                              serverHost='aol.com',
                              serverPort=70,
                              serverProtocol='gopher',
                              serverAuthToken='token',
                              clientId='test-fuzzer1',
                              tool='test-tool')
        collector._session.get = myget

        # call refresh
        collector.refresh()

    # check that it worked
    assert {f.name for f in sigs_path.iterdir()} == {'test2.signature', 'other.txt'}
    assert (sigs_path / 'test2.signature').read_text() == 'test2'
    assert 'other.txt' in capsys.readouterr()[1]  # should have had a warning about unrecognized file

    # check that 404 raises

    class response_t(object):  # noqa
        status_code = requests.codes["not found"]
        text = "Not found"
    collector._session.get = lambda *_, **__: response_t()

    with pytest.raises(RuntimeError, match='Server unexpectedly responded'):
        collector.refresh()

    # check that bad zips raise errors
    with (sigs_path / 'other.txt').open('rb') as fp:
        class response_t(object):  # noqa
            status_code = requests.codes["ok"]
            text = "OK"
            raw = fp
        collector._session.get = lambda *_, **__: response_t()

        with pytest.raises(zipfile.BadZipfile, match='not a zip file'):
            collector.refresh()

    with outzip_path.open('r+b') as fp:
        # corrupt the CRC field for the signature file in the zip
        fp.seek(0x42)
        fp.write(b'\xFF')
    with outzip_path.open('rb') as fp:
        class response_t(object):  # noqa
            status_code = requests.codes["ok"]
            text = "OK"
            raw = fp
        collector._session.get = lambda *_, **__: response_t()

        with pytest.raises(RuntimeError, match='Bad CRC'):
            collector.refresh()


def test_collector_generate_search(tmp_path):
    '''Test sigcache generation and search'''
    # create a cache dir
    cache_dir = tmp_path / 'sigcache'
    cache_dir.mkdir()

    # create a collector
    collector = Collector(sigCacheDir=str(cache_dir))

    # generate a signature from the crash data
    config = ProgramConfiguration('mozilla-central', 'x86-64', 'linux', version='ba0bc4f26681')
    crashInfo = CrashInfo.fromRawCrashData([], asanTraceCrash.splitlines(), config)
    sig = collector.generate(crashInfo, False, False, 8)
    assert {str(f) for f in cache_dir.iterdir()} == {sig}

    # search the sigcache and see that it matches the original
    sigMatch, meta = collector.search(crashInfo)
    assert sigMatch == sig
    assert meta is None

    # write metadata and make sure that's returned if it exists
    sigBase, _ = os.path.splitext(sig)
    with open(sigBase + '.metadata', 'w') as f:
        f.write('{}')
    sigMatch, meta = collector.search(crashInfo)
    assert sigMatch == sig
    assert meta == {}

    # make sure another crash doesn't match
    crashInfo = CrashInfo.fromRawCrashData([], [], config)
    sigMatch, meta = collector.search(crashInfo)
    assert sigMatch is None
    assert meta is None

    # returns None if sig generation fails
    result = collector.generate(crashInfo, True, True, 8)
    assert result is None


def test_collector_download(tmp_path, monkeypatch):
    '''Test testcase downloads'''
    # create Collector
    collector = Collector(serverHost='aol.com',
                          serverPort=70,
                          serverProtocol='gopher',
                          serverAuthToken='token',
                          tool='test-tool')

    class response1_t(object):
        status_code = requests.codes["ok"]
        text = 'OK'

        def json(self):
            return {'id': 123, 'testcase': 'path/to/testcase.txt'}

    class response2_t(object):
        status_code = requests.codes["ok"]
        headers = {'content-disposition': 'foo'}
        text = 'OK'
        content = b'testcase\xFF'

    # myget1 mocks requests.get to return the rest response to the crashentry get
    def myget1(url, headers=None):
        assert url == 'gopher://aol.com:70/crashmanager/rest/crashes/123/'
        assert headers == {'Authorization': 'Token token'}

        monkeypatch.chdir(str(tmp_path))  # download writes to cwd, so make that tmp
        collector._session.get = myget2
        return response1_t()

    # myget2 mocks requests.get to return the testcase data specified in myget1
    def myget2(url, headers=None):
        assert url == 'gopher://aol.com:70/crashmanager/rest/crashes/123/download/'
        assert headers == {'Authorization': 'Token token'}
        return response2_t()
    collector._session.get = myget1

    # call refresh
    collector.download(123)

    # check that it worked
    assert {f.name for f in tmp_path.iterdir()} == {'123.txt'}
    with open('123.txt', 'rb') as fp:
        assert fp.read() == response2_t.content

    # testcase GET returns http error
    class response2_t(object):
        status_code = 404
        text = 'Not found'
    collector._session.get = myget1
    with pytest.raises(RuntimeError, match='Server unexpectedly responded'):
        collector.download(123)

    # download with no testcase
    class response1_t(object):  # noqa
        status_code = requests.codes["ok"]
        text = 'OK'

        def json(self):
            return {'testcase': ''}
    collector._session.get = myget1
    result = collector.download(123)
    assert result is None

    # invalid REST response
    class response1_t(object):  # noqa
        status_code = requests.codes["ok"]
        text = 'OK'

        def json(self):
            return []
    collector._session.get = myget1
    with pytest.raises(RuntimeError, match='malformed JSON'):
        collector.download(123)

    # REST query returns http error
    class response1_t(object):  # noqa
        status_code = 404
        text = 'Not found'
    collector._session.get = myget1
    with pytest.raises(RuntimeError, match='Server unexpectedly responded'):
        collector.download(123)
