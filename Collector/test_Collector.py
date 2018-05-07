'''
Tests

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''
from __future__ import absolute_import
import json
import os
import platform
import time
import zipfile

import pytest
import requests
from six.moves.urllib.parse import urlsplit

from Collector.Collector import Collector, main
from FTB.Signatures.CrashInfo import CrashInfo
from FTB.ProgramConfiguration import ProgramConfiguration
from crashmanager.models import CrashEntry

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

pytest_plugins = 'server.tests'


def test_collector_help(capsys):
    '''Test that help prints without throwing'''
    with pytest.raises(SystemExit):
        main()
    _, err = capsys.readouterr()
    assert err.startswith('usage: ')


def test_collector_submit(live_server, tmpdir, fm_user, monkeypatch):
    '''Test crash submission'''
    monkeypatch.setattr(os.path, 'expanduser', lambda path: tmpdir.strpath)  # ensure fuzzmanager config is not used
    monkeypatch.setattr(time, 'sleep', lambda t: None)

    # create a collector
    url = urlsplit(live_server.url)
    collector = Collector(sigCacheDir=tmpdir.mkdir('sigcache').strpath,
                          serverHost=url.hostname,
                          serverPort=url.port,
                          serverProtocol=url.scheme,
                          serverAuthToken=fm_user.token,
                          clientId='test-fuzzer1',
                          tool='test-tool')
    testcase_path = tmpdir.mkdir('testcase').join('testcase.js').strpath
    with open(testcase_path, 'wb') as testcase_fp:
        testcase_fp.write(exampleTestCase)
    config = ProgramConfiguration('mozilla-central', 'x86-64', 'linux', version='ba0bc4f26681')
    crashInfo = CrashInfo.fromRawCrashData([], asanTraceCrash.splitlines(), config)

    # submit a crash to test server using collector
    result = collector.submit(crashInfo, testcase_path)

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
    with open(tmpdir.join('.fuzzmanagerconf').strpath, 'w') as fp:
        fp.write('[Main]\n')
        fp.write('serverhost = %s\n' % url.hostname)
        fp.write('serverport = %d\n' % url.port)
        fp.write('serverproto = %s\n' % url.scheme)
        fp.write('serverauthtoken = %s\n' % fm_user.token)

    # try a binary testcase via cmd line
    testcase_path = tmpdir.join('testcase.bin').strpath
    with open(testcase_path, 'wb') as testcase_fp:
        testcase_fp.write(b'\0')
    stdout = tmpdir.join('stdout.txt').strpath
    with open(stdout, 'w') as fp:
        fp.write('stdout data')
    stderr = tmpdir.join('stderr.txt').strpath
    with open(stderr, 'w') as fp:
        fp.write('stderr data')
    crashdata = tmpdir.join('crashdata.txt').strpath
    with open(crashdata, 'w') as fp:
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
        '--testcase', testcase_path,
        '--testcasequality', '5',
        '--stdout', stdout,
        '--stderr', stderr,
        '--crashdata', crashdata,
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

    def mypost(_session, _url, _data, headers=None):
        return response_t()
    monkeypatch.setattr(time, 'sleep', lambda t: None)
    monkeypatch.setattr(requests.Session, 'post', mypost)
    with pytest.raises(RuntimeError, match='Server unexpectedly responded'):
        collector.submit(crashInfo, testcase_path)


def test_collector_refresh(tmpdir, monkeypatch, capsys):
    '''Test signature downloads'''
    # create a test signature zip
    test2 = tmpdir.join('test2.signature').strpath
    with open(test2, 'w') as fp:
        fp.write('test2')
    with zipfile.ZipFile(tmpdir.join('out.zip').strpath, 'w') as zf:
        zf.write(test2, 'test2.signature')

    # create an old signature
    tmpdir.mkdir('sigs')
    with open(tmpdir.join('sigs', 'test1.signature').strpath, 'w'):
        pass
    with open(tmpdir.join('sigs', 'other.txt').strpath, 'w'):
        pass
    assert {f.basename for f in tmpdir.join('sigs').listdir()} == {'test1.signature', 'other.txt'}

    with open(tmpdir.join('out.zip').strpath, 'rb') as fp:
        class response_t(object):
            status_code = requests.codes["ok"]
            text = "OK"
            raw = fp

        # this asserts the expected arguments and returns the open handle to out.zip as 'raw' which is read by refresh()
        def myget(_session, url, stream=None, headers=None):
            assert url == 'gopher://aol.com:70/crashmanager/rest/signatures/download/'
            assert stream is True
            assert headers == {'Authorization': 'Token token'}
            return response_t()
        monkeypatch.setattr(requests.Session, 'get', myget)

        # create Collector
        collector = Collector(sigCacheDir=tmpdir.join('sigs').strpath,
                              serverHost='aol.com',
                              serverPort=70,
                              serverProtocol='gopher',
                              serverAuthToken='token',
                              clientId='test-fuzzer1',
                              tool='test-tool')

        # call refresh
        collector.refresh()

    # check that it worked
    assert {f.basename for f in tmpdir.join('sigs').listdir()} == {'test2.signature', 'other.txt'}
    with open(tmpdir.join('sigs', 'test2.signature').strpath) as fp:
        assert fp.read() == 'test2'
    assert 'other.txt' in capsys.readouterr()[1]  # should have had a warning about unrecognized file

    # check that 404 raises
    monkeypatch.undo()

    class response_t(object):  # noqa
        status_code = requests.codes["not found"]
        text = "Not found"

    def myget(_session, _url, stream=None, headers=None):
        return response_t()
    monkeypatch.setattr(requests.Session, 'get', myget)
    with pytest.raises(RuntimeError, match='Server unexpectedly responded'):
        collector.refresh()

    # check that bad zips raise errors
    monkeypatch.undo()
    with open(tmpdir.join('sigs', 'other.txt').strpath, 'rb') as fp:
        class response_t(object):  # noqa
            status_code = requests.codes["ok"]
            text = "OK"
            raw = fp

        def myget(_session, _url, stream=None, headers=None):
            return response_t()
        monkeypatch.setattr(requests.Session, 'get', myget)
        with pytest.raises(zipfile.BadZipfile, match='not a zip file'):
            collector.refresh()
    monkeypatch.undo()
    with open(tmpdir.join('out.zip').strpath, 'r+b') as fp:
        # corrupt the CRC field for the signature file in the zip
        fp.seek(0x42)
        fp.write(b'\xFF')
    with open(tmpdir.join('out.zip').strpath, 'rb') as fp:
        class response_t(object):  # noqa
            status_code = requests.codes["ok"]
            text = "OK"
            raw = fp

        def myget(_session, _url, stream=None, headers=None):
            return response_t()
        monkeypatch.setattr(requests.Session, 'get', myget)
        with pytest.raises(RuntimeError, match='Bad CRC'):
            collector.refresh()


def test_collector_generate_search(tmpdir):
    '''Test sigcache generation and search'''
    # create a cache dir
    cache_dir = tmpdir.mkdir('sigcache').strpath

    # create a collector
    collector = Collector(sigCacheDir=cache_dir)

    # generate a signature from the crash data
    config = ProgramConfiguration('mozilla-central', 'x86-64', 'linux', version='ba0bc4f26681')
    crashInfo = CrashInfo.fromRawCrashData([], asanTraceCrash.splitlines(), config)
    sig = collector.generate(crashInfo, False, False, 8)
    assert {f.strpath for f in tmpdir.join('sigcache').listdir()} == {sig}

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


def test_collector_download(tmpdir, monkeypatch):
    '''Test testcase downloads'''
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
    def myget1(_session, url, headers=None):
        assert url == 'gopher://aol.com:70/crashmanager/rest/crashes/123/'
        assert headers == {'Authorization': 'Token token'}

        monkeypatch.undo()
        monkeypatch.chdir(tmpdir)  # download writes to cwd, so make that tmpdir
        monkeypatch.setattr(requests.Session, 'get', myget2)
        return response1_t()

    # myget2 mocks requests.get to return the testcase data specified in myget1
    def myget2(_session, url, headers=None):
        assert url == 'gopher://aol.com:70/crashmanager/rest/crashes/123/download/'
        assert headers == {'Authorization': 'Token token'}
        return response2_t()
    monkeypatch.setattr(requests.Session, 'get', myget1)

    # create Collector
    collector = Collector(serverHost='aol.com',
                          serverPort=70,
                          serverProtocol='gopher',
                          serverAuthToken='token',
                          tool='test-tool')

    # call refresh
    collector.download(123)

    # check that it worked
    assert {f.basename for f in tmpdir.listdir()} == {'123.txt'}
    with open('123.txt', 'rb') as fp:
        assert fp.read() == response2_t.content

    # testcase GET returns http error
    class response2_t(object):
        status_code = 404
        text = 'Not found'
    monkeypatch.undo()
    monkeypatch.setattr(requests.Session, 'get', myget1)
    with pytest.raises(RuntimeError, match='Server unexpectedly responded'):
        collector.download(123)

    # download with no testcase
    class response1_t(object):  # noqa
        status_code = requests.codes["ok"]
        text = 'OK'

        def json(self):
            return {'testcase': ''}
    monkeypatch.undo()
    monkeypatch.setattr(requests.Session, 'get', myget1)
    result = collector.download(123)
    assert result is None

    # invalid REST response
    class response1_t(object):  # noqa
        status_code = requests.codes["ok"]
        text = 'OK'

        def json(self):
            return []
    monkeypatch.undo()
    monkeypatch.setattr(requests.Session, 'get', myget1)
    with pytest.raises(RuntimeError, match='malformed JSON'):
        collector.download(123)

    # REST query returns http error
    class response1_t(object):  # noqa
        status_code = 404
        text = 'Not found'
    monkeypatch.undo()
    monkeypatch.setattr(requests.Session, 'get', myget1)
    with pytest.raises(RuntimeError, match='Server unexpectedly responded'):
        collector.download(123)
