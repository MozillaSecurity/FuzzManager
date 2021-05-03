# coding: utf-8
'''
Tests for signatures view.

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''
import json
import logging
import pytest
import requests
from django.urls import reverse
from crashmanager.models import Bucket, BucketWatch, CrashEntry
from . import assert_contains


LOG = logging.getLogger("fm.crashmanager.tests.signatures")
ALL_SIGS_FMT = "Displaying all %d signature entries in the database."
SIGS_FMT = "Displaying %d unreported signature entries from the database."
pytestmark = pytest.mark.usefixtures("crashmanager_test")  # pylint: disable=invalid-name


# pylint: disable=no-self-use
@pytest.mark.parametrize(("name", "entries_fmt"),
                         [("crashmanager:signatures", SIGS_FMT),
                          ("crashmanager:allsignatures", ALL_SIGS_FMT)])
class TestSignaturesViews(object):
    """Common signatures tests"""

    def test_signatures_view_no_sigs(self, client, name, entries_fmt):
        """If no sigs in db, an appropriate message is shown."""
        client.login(username='test', password='test')
        response = client.get(reverse(name))
        LOG.debug(response)
        assert response.status_code == requests.codes['ok']
        siglist = response.context['siglist']
        assert not siglist  # 0 buckets
        assert_contains(response, entries_fmt % 0)

    def test_signatures_view_with_sig(self, client, cm, name, entries_fmt):  # pylint: disable=invalid-name
        """Create one bucket and check that it is shown ok."""
        client.login(username='test', password='test')
        bucket = cm.create_bucket(shortDescription="bucket #1")
        response = client.get(reverse(name))
        LOG.debug(response)
        assert response.status_code == requests.codes['ok']
        siglist = response.context['siglist']
        assert len(siglist) == 1  # 1 bucket
        assert siglist[0] == bucket  # same bucket we created
        assert_contains(response, "bucket #1")
        assert_contains(response, entries_fmt % 1)

    def test_signatures_view_with_sigs(self, client, cm, name, entries_fmt):  # pylint: disable=invalid-name
        """Create two buckets and check that they are shown ok."""
        client.login(username='test', password='test')
        buckets = (cm.create_bucket(shortDescription="bucket #1"),
                   cm.create_bucket(shortDescription="bucket #2"))
        response = client.get(reverse(name))
        LOG.debug(response)
        assert response.status_code == requests.codes['ok']
        siglist = response.context['siglist']
        assert len(siglist) == 2  # 2 buckets
        assert set(siglist) == set(buckets)  # same buckets we created
        assert_contains(response, "bucket #1")
        assert_contains(response, "bucket #2")
        assert_contains(response, entries_fmt % 2)


@pytest.mark.parametrize(("name", "kwargs"), [("crashmanager:signatures", {}),
                                              ("crashmanager:allsignatures", {}),
                                              ("crashmanager:findsigs", {'crashid': 0}),
                                              ("crashmanager:siglink", {'sigid': 0}),
                                              ("crashmanager:sigunlink", {'sigid': 0}),
                                              ("crashmanager:sigopt", {'sigid': 0}),
                                              ("crashmanager:sigtry", {'sigid': 0, 'crashid': 0}),
                                              ("crashmanager:signew", {}),
                                              ("crashmanager:sigedit", {'sigid': 1})])
def test_signatures_no_login(client, name, kwargs):
    """Request without login hits the login redirect"""
    path = reverse(name, kwargs=kwargs)
    resp = client.get(path)
    assert resp.status_code == requests.codes['found']
    assert resp.url == '/login/?next=' + path


def test_signatures_view_logged(client, cm):  # pylint: disable=invalid-name
    """Create a bucket and mark it logged, see that no entries are shown."""
    client.login(username='test', password='test')
    cm.create_bucket(shortDescription="bucket #1", bug=cm.create_bug('123'))
    response = client.get(reverse("crashmanager:signatures"))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']
    siglist = response.context['siglist']
    assert not siglist.count()  # 0 buckets
    assert_contains(response, SIGS_FMT % 0)


def test_signatures_view_logged_unlogged(client, cm):  # pylint: disable=invalid-name
    """Create two buckets and mark one logged, see that only unlogged entry is shown."""
    client.login(username='test', password='test')
    bucket = cm.create_bucket(shortDescription="bucket #1")
    cm.create_bucket(shortDescription="bucket #2", bug=cm.create_bug('123'))
    response = client.get(reverse("crashmanager:signatures"))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']
    siglist = response.context['siglist']
    assert len(siglist) == 1  # 1 bucket
    assert siglist[0] == bucket  # same bucket we created
    assert_contains(response, "bucket #1")
    assert_contains(response, SIGS_FMT % 1)


def test_signatures_view_toolfilter(client, cm):  # pylint: disable=invalid-name
    """Check that toolfilter affects bucket size."""
    client.login(username='test', password='test')
    bucket1 = cm.create_bucket(shortDescription="bucket #1")
    bucket2 = cm.create_bucket(shortDescription="bucket #2")
    cm.create_crash(shortSignature="crash #1", tool="tool #1", bucket=bucket1)
    cm.create_crash(shortSignature="crash #2", tool="tool #2", bucket=bucket1)
    cm.create_crash(shortSignature="crash #3", tool="tool #1", bucket=bucket1)
    cm.create_crash(shortSignature="crash #4", tool="tool #1", bucket=bucket2)
    cm.create_toolfilter("tool #1")
    response = client.get(reverse("crashmanager:signatures"))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']
    siglist = response.context['siglist']
    LOG.debug(siglist)
    assert len(siglist) == 2  # 2 buckets
    assert siglist[0] == bucket2
    assert siglist[0].size == 1
    assert siglist[1] == bucket1
    assert siglist[1].size == 2
    assert_contains(response, "bucket #1")
    assert_contains(response, "bucket #2")
    assert_contains(response, SIGS_FMT % 2)


def test_all_signatures_view_logged(client, cm):  # pylint: disable=invalid-name
    """Create a bucket, mark logged, and see that /all/ still shows the entry."""
    client.login(username='test', password='test')
    bucket = cm.create_bucket(shortDescription="bucket #1", bug=cm.create_bug('123'))
    response = client.get(reverse("crashmanager:allsignatures"))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']
    assert_contains(response, "bucket #1")
    siglist = response.context['siglist']
    assert len(siglist) == 1  # 1 bucket
    assert siglist[0] == bucket  # same bucket we created
    assert_contains(response, ALL_SIGS_FMT % 1)


def test_all_signatures_view_logged_unlogged(client, cm):  # pylint: disable=invalid-name
    """Create a bucket, mark logged, and see that /all/ shows both entries."""
    client.login(username='test', password='test')
    buckets = (cm.create_bucket(shortDescription="bucket #1"),
               cm.create_bucket(shortDescription="bucket #2", bug=cm.create_bug('123')))
    response = client.get(reverse("crashmanager:allsignatures"))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']
    siglist = response.context['siglist']
    assert len(siglist) == 2  # 2 buckets
    assert set(siglist) == set(buckets)  # same buckets we created
    assert_contains(response, "bucket #1")
    assert_contains(response, "bucket #2")
    assert_contains(response, ALL_SIGS_FMT % 2)


def test_all_signatures_view_toolfilter(client, cm):  # pylint: disable=invalid-name
    """Check that toolfilter is ignored in /all/."""
    client.login(username='test', password='test')
    bucket1 = cm.create_bucket(shortDescription="bucket #1")
    bucket2 = cm.create_bucket(shortDescription="bucket #2")
    cm.create_crash(shortSignature="crash #1", tool="tool #1", bucket=bucket1)
    cm.create_crash(shortSignature="crash #2", tool="tool #2", bucket=bucket1)
    cm.create_crash(shortSignature="crash #3", tool="tool #1", bucket=bucket1)
    cm.create_crash(shortSignature="crash #4", tool="tool #1", bucket=bucket2)
    cm.create_toolfilter("tool #1")
    response = client.get(reverse("crashmanager:allsignatures"))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']
    siglist = response.context['siglist']
    LOG.debug(siglist)
    assert len(siglist) == 2  # 2 buckets
    assert siglist[0] == bucket2
    assert siglist[0].size == 1
    assert siglist[1] == bucket1
    assert siglist[1].size == 3
    assert_contains(response, "bucket #1")
    assert_contains(response, "bucket #2")
    assert_contains(response, ALL_SIGS_FMT % 2)


def test_del_signature_simple_get(client, cm):  # pylint: disable=invalid-name
    """No errors are thrown in template"""
    client.login(username='test', password='test')
    bucket = cm.create_bucket(shortDescription='bucket #1')
    response = client.get(reverse("crashmanager:sigdel", kwargs={"sigid": bucket.pk}))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']
    assert_contains(response, "Are you sure that you want to delete this signature?")
    assert_contains(response, "Also delete all %d entries with this bucket" % 0)
    cm.create_crash(shortSignature='crash #1', bucket=bucket)
    response = client.get(reverse("crashmanager:sigdel", kwargs={"sigid": bucket.pk}))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']
    assert_contains(response, "Are you sure that you want to delete this signature?")
    assert_contains(response, "Also delete all %d entries with this bucket" % 1)


def test_find_signature_simple_get(client, cm):  # pylint: disable=invalid-name
    """No errors are thrown in template"""
    client.login(username='test', password='test')
    crash = cm.create_crash()
    cm.create_bucket(signature=json.dumps({"symptoms": [
        {'src': 'stderr',
         'type': 'output',
         'value': '//'}]}))

    response = client.get(reverse("crashmanager:findsigs", kwargs={"crashid": crash.pk}))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']


def test_link_signature_simple_get(client, cm):  # pylint: disable=invalid-name
    """No errors are thrown in template"""
    client.login(username='test', password='test')
    bucket = cm.create_bucket()
    response = client.get(reverse("crashmanager:siglink", kwargs={"sigid": bucket.pk}))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']


def test_unlink_signature_simple_get(client, cm):  # pylint: disable=invalid-name
    """No errors are thrown in template"""
    client.login(username='test', password='test')
    bucket = cm.create_bucket()
    response = client.get(reverse("crashmanager:sigunlink", kwargs={"sigid": bucket.pk}))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']


def test_opt_signature_simple_get(client, cm):  # pylint: disable=invalid-name
    """No errors are thrown in template"""
    client.login(username='test', password='test')
    bucket = cm.create_bucket(signature=json.dumps({"symptoms": [
        {'src': 'stderr',
         'type': 'output',
         'value': '//'}]}))
    response = client.get(reverse("crashmanager:sigopt", kwargs={"sigid": bucket.pk}))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']


def test_try_signature_simple_get(client, cm):  # pylint: disable=invalid-name
    """No errors are thrown in template"""
    client.login(username='test', password='test')
    bucket = cm.create_bucket(signature=json.dumps({"symptoms": [
        {'src': 'stderr',
         'type': 'output',
         'value': '//'}]}))
    crash = cm.create_crash()
    response = client.get(reverse("crashmanager:sigtry", kwargs={"sigid": bucket.pk, "crashid": crash.pk}))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']


def test_new_signature_view(client):
    """Check that the Vue component is called"""
    client.login(username='test', password='test')
    response = client.get(reverse("crashmanager:signew"))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']
    assert_contains(response, 'createoredit')


def test_edit_signature_view(client, cm):  # pylint: disable=invalid-name
    """Check that the Vue component is called"""
    client.login(username='test', password='test')
    sig = json.dumps({
        'symptoms': [
            {"src": "stderr",
             "type": "output",
             "value": "/^blah/"}
        ]
    })
    bucket = cm.create_bucket(shortDescription="bucket #1", signature=sig)
    response = client.get(reverse("crashmanager:sigedit", kwargs={'sigid': bucket.pk}))
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']
    assert_contains(response, 'createoredit')
    assert response.context['bucketId'] == bucket.pk


def test_del_signature_empty(client, cm):  # pylint: disable=invalid-name
    """Test deleting a signature with no crashes"""
    client.login(username='test', password='test')
    bucket = cm.create_bucket(shortDescription='bucket #1')
    response = client.post(reverse("crashmanager:sigdel", kwargs={"sigid": bucket.pk}))
    LOG.debug(response)
    assert response.status_code == requests.codes['found']
    assert response.url == reverse('crashmanager:signatures')
    assert not Bucket.objects.count()


def test_del_signature_leave_entries(client, cm):  # pylint: disable=invalid-name
    """Test deleting a signature with crashes and leave entries"""
    client.login(username='test', password='test')
    bucket = cm.create_bucket(shortDescription='bucket #1')
    crash = cm.create_crash(shortSignature='crash #1', bucket=bucket)
    response = client.post(reverse("crashmanager:sigdel", kwargs={"sigid": bucket.pk}))
    LOG.debug(response)
    assert response.status_code == requests.codes['found']
    assert response.url == reverse('crashmanager:signatures')
    assert not Bucket.objects.count()
    crash = CrashEntry.objects.get(pk=crash.pk)  # re-read
    assert crash.bucket is None


def test_del_signature_del_entries(client, cm):  # pylint: disable=invalid-name
    """Test deleting a signature with crashes and removing entries"""
    client.login(username='test', password='test')
    bucket = cm.create_bucket(shortDescription='bucket #1')
    cm.create_crash(shortSignature='crash #1', bucket=bucket)
    response = client.post(reverse("crashmanager:sigdel", kwargs={"sigid": bucket.pk}), {'delentries': '1'})
    LOG.debug(response)
    assert response.status_code == requests.codes['found']
    assert response.url == reverse('crashmanager:signatures')
    assert not Bucket.objects.count()
    assert not CrashEntry.objects.count()


def test_watch_signature_empty(client):
    """If no watched signatures, that should be shown"""
    client.login(username='test', password='test')
    response = client.get(reverse('crashmanager:sigwatch'))
    LOG.debug(response)
    assert_contains(response, "Displaying 0 watched signature entries from the database.")


def test_watch_signature_buckets(client, cm):  # pylint: disable=invalid-name
    """Watched signatures should be listed"""
    client.login(username='test', password='test')
    bucket = cm.create_bucket(shortDescription='bucket #1')
    cm.create_bucketwatch(bucket=bucket)
    response = client.get(reverse('crashmanager:sigwatch'))
    LOG.debug(response)
    assert_contains(response, "Displaying 1 watched signature entries from the database.")
    siglist = response.context['siglist']
    assert len(siglist) == 1
    assert siglist[0] == bucket


def test_watch_signature_buckets_new_crashes(client, cm):  # pylint: disable=invalid-name
    """Watched signatures should show new crashes"""
    client.login(username='test', password='test')
    buckets = (cm.create_bucket(shortDescription='bucket #1'),
               cm.create_bucket(shortDescription='bucket #2'))
    crash1 = cm.create_crash(shortSignature='crash #1', bucket=buckets[1], tool='tool #1')
    cm.create_toolfilter('tool #1')
    cm.create_bucketwatch(bucket=buckets[0])
    cm.create_bucketwatch(bucket=buckets[1], crash=crash1)
    cm.create_crash(shortSignature='crash #2', bucket=buckets[1], tool='tool #1')
    response = client.get(reverse('crashmanager:sigwatch'))
    LOG.debug(response)
    assert_contains(response, "Displaying 2 watched signature entries from the database.")
    siglist = response.context['siglist']
    assert len(siglist) == 2
    assert siglist[0] == buckets[1]
    assert siglist[0].newCrashes == 1
    assert siglist[1] == buckets[0]
    assert not siglist[1].newCrashes


def test_watch_signature_del(client, cm):  # pylint: disable=invalid-name
    """Deleting a signature watch"""
    client.login(username='test', password='test')
    bucket = cm.create_bucket(shortDescription='bucket #1')
    cm.create_bucketwatch(bucket=bucket)
    response = client.get(reverse('crashmanager:sigwatchdel', kwargs={"sigid": bucket.pk}))
    LOG.debug(response)
    assert_contains(response, "Are you sure that you want to stop watching this signature for new crash entries?")
    assert_contains(response, bucket.shortDescription)
    response = client.post(reverse('crashmanager:sigwatchdel', kwargs={"sigid": bucket.pk}))
    LOG.debug(response)
    assert not BucketWatch.objects.count()
    assert Bucket.objects.get() == bucket
    assert response.status_code == requests.codes['found']
    assert response.url == reverse('crashmanager:sigwatch')


def test_watch_signature_delsig(client, cm):  # pylint: disable=invalid-name
    """Deleting a watched signature"""
    client.login(username='test', password='test')
    bucket = cm.create_bucket(shortDescription='bucket #1')
    cm.create_bucketwatch(bucket=bucket)
    bucket.delete()
    assert not BucketWatch.objects.count()


def test_watch_signature_update(client, cm):  # pylint: disable=invalid-name
    """Updating a signature watch"""
    client.login(username='test', password='test')
    bucket = cm.create_bucket(shortDescription="bucket #1")
    crash1 = cm.create_crash(shortSignature='crash #1', bucket=bucket)
    watch = cm.create_bucketwatch(bucket=bucket, crash=crash1)
    crash2 = cm.create_crash(shortSignature='crash #2', bucket=bucket)
    response = client.post(reverse('crashmanager:sigwatchnew'), {"bucket": "%d" % bucket.pk,
                                                                 "crash": "%d" % crash2.pk})
    LOG.debug(response)
    assert response.status_code == requests.codes['found']
    assert response.url == reverse('crashmanager:sigwatch')
    watch = BucketWatch.objects.get(pk=watch.pk)
    assert watch.bucket == bucket
    assert watch.lastCrash == crash2.pk


def test_watch_signature_new(client, cm):  # pylint: disable=invalid-name
    """Creating a signature watch"""
    client.login(username='test', password='test')
    bucket = cm.create_bucket(shortDescription="bucket #1")
    crash = cm.create_crash(shortSignature='crash #1', bucket=bucket)
    response = client.post(reverse('crashmanager:sigwatchnew'), {"bucket": "%d" % bucket.pk,
                                                                 "crash": "%d" % crash.pk})
    LOG.debug(response)
    assert response.status_code == requests.codes['found']
    assert response.url == reverse('crashmanager:sigwatch')
    watch = BucketWatch.objects.get()
    assert watch.bucket == bucket
    assert watch.lastCrash == crash.pk


def test_watch_signature_crashes(client, cm):  # pylint: disable=invalid-name
    """Crashes in a signature watch should be shown correctly."""
    client.login(username='test', password='test')
    bucket = cm.create_bucket(shortDescription='bucket #1')
    crash1 = cm.create_crash(shortSignature='crash #1', bucket=bucket)
    url = reverse("crashmanager:sigwatchcrashes", kwargs={"sigid": bucket.pk})
    watch = cm.create_bucketwatch(bucket=bucket)
    # check that crash1 is shown
    response = client.get(url)
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']
    crashes = response.context['crashlist']
    assert len(crashes) == 1
    assert crashes[0] == crash1
    watch.lastCrash = crash1.pk
    watch.save()
    # check that no crashes are shown
    response = client.get(url)
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']
    crashes = response.context['crashlist']
    assert not crashes
    crash2 = cm.create_crash(shortSignature='crash #2', bucket=bucket)
    # check that crash2 is shown
    response = client.get(url)
    LOG.debug(response)
    assert response.status_code == requests.codes['ok']
    crashes = response.context['crashlist']
    assert len(crashes) == 1
    assert crashes[0] == crash2
