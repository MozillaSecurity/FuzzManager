'''
Tests

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''
import os
import sys
import zipfile
if sys.version_info.major == 3:
    from urllib.parse import urlsplit
else:
    from urlparse import urlsplit

import pytest
import requests
from requests.exceptions import ConnectionError

from Collector import Collector, main
from FTB.Signatures.CrashInfo import CrashInfo
from FTB.ProgramConfiguration import ProgramConfiguration
from FTB.Signatures.CrashSignature import CrashSignature
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
==5854==ABORTING'''

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


def test_collector_submit(live_server, tmpdir, fm_user):
    '''Test crash submission'''
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
    with open(testcase_path, 'w') as testcase_fp:
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


def test_collector_refresh(tmpdir, monkeypatch):
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
    assert {f.basename for f in tmpdir.join('sigs').listdir()} == {'test1.signature'}

    with open(tmpdir.join('out.zip').strpath, 'rb') as fp:
        class response_t(object):
            status_code = requests.codes["ok"]
            text = "OK"
            raw = fp
        # this asserts the expected arguments, and returns the open handle to out.zip as 'raw' which is read by refresh()
        def myget(url, stream=None, auth=None):
            assert url == 'gopher://aol.com:70/crashmanager/files/signatures.zip'
            assert stream is True
            assert len(auth) == 2
            assert auth[0] == 'fuzzmanager'
            assert auth[1] == 'token'
            return response_t()
        monkeypatch.setattr(requests, 'get', myget)

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
    assert {f.basename for f in tmpdir.join('sigs').listdir()} == {'test2.signature'}
    with open(tmpdir.join('sigs', 'test2.signature').strpath) as fp:
        assert fp.read() == 'test2'


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


def test_collector_download(tmpdir, monkeypatch):
    '''Test testcase downloads'''
    class response1_t(object):
        status_code = requests.codes["ok"]
        text = 'OK'
        def json(self):
            return {'testcase': 'path/to/testcase.txt'}
    class response2_t(object):
        status_code = requests.codes["ok"]
        text = 'OK'
        content = b'testcase\xFF'
    # myget1 mocks requests.get to return the rest response to the crashentry get
    def myget1(url, headers=None):
        assert url == 'gopher://aol.com:70/crashmanager/rest/crashes/123/'
        assert headers == {'Authorization':'Token token'}
        monkeypatch.undo()
        monkeypatch.chdir(tmpdir)  # download writes to cwd, so make that tmpdir
        monkeypatch.setattr(requests, 'get', myget2)
        return response1_t()
    # myget2 mocks requests.get to return the testcase data specified in myget1
    def myget2(url, auth=None):
        assert url == 'gopher://aol.com:70/crashmanager/path/to/testcase.txt'
        assert len(auth) == 2
        assert auth[0] == 'fuzzmanager'
        assert auth[1] == 'token'
        return response2_t()
    monkeypatch.setattr(requests, 'get', myget1)

    # create Collector
    collector = Collector(serverHost='aol.com',
                          serverPort=70,
                          serverProtocol='gopher',
                          serverAuthToken='token',
                          tool='test-tool')

    # call refresh
    collector.download(123)

    # check that it worked
    assert {f.basename for f in tmpdir.listdir()} == {'testcase.txt'}
    with open('testcase.txt', 'rb') as fp:
        assert fp.read() == response2_t.content
