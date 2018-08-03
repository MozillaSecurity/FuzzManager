'''
Tests for Pool views.

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import logging

import requests
from django.core.urlresolvers import reverse
# from moto import mock_ec2_deprecated

from . import TestCase


log = logging.getLogger("fm.ec2spotmanager.tests.pools")  # pylint: disable=invalid-name


class PoolsViewTests(TestCase):
    name = "ec2spotmanager:pools"
    entries_fmt = "Displaying all %d instance pools:"

    def test_no_login(self):
        """Request without login hits the login redirect"""
        path = reverse(self.name)
        self.assertRedirects(self.client.get(path), '/login/?next=' + path)

    def test_no_pools(self):
        """If no pools in db, an appropriate message is shown."""
        self.client.login(username='test', password='test')
        response = self.client.get(reverse(self.name))
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])
        poollist = response.context['poollist']
        self.assertEqual(len(poollist), 0)  # 0 pools
        self.assertContains(response, self.entries_fmt % 0)

    def test_pool(self):
        """Create pool and see that it is shown."""
        config = self.create_config(name='config #1')
        pool = self.create_pool(config=config)
        self.client.login(username='test', password='test')
        response = self.client.get(reverse(self.name))
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])
        poollist = response.context['poollist']
        self.assertEqual(len(poollist), 1)  # 1 pools
        self.assertContains(response, self.entries_fmt % 1)
        self.assertEqual(set(poollist), {pool})

    def test_pools(self):
        """Create pool and see that it is shown."""
        configs = (self.create_config(name='config #1'),
                   self.create_config(name='config #2'))
        pools = [self.create_pool(config=cfg) for cfg in configs]
        self.client.login(username='test', password='test')
        response = self.client.get(reverse(self.name))
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])
        poollist = response.context['poollist']
        self.assertEqual(len(poollist), 2)  # 2 pools
        self.assertContains(response, self.entries_fmt % 2)
        self.assertEqual(set(poollist), set(pools))


class CreatePoolViewTests(TestCase):
    name = "ec2spotmanager:poolcreate"

    def test_no_login(self):
        """Request without login hits the login redirect"""
        path = reverse(self.name)
        self.assertRedirects(self.client.get(path), '/login/?next=' + path)

    def test_simpleget(self):
        """No errors are thrown in template"""
        self.client.login(username='test', password='test')
        response = self.client.get(reverse(self.name))
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])


class ViewPoolViewTests(TestCase):
    name = "ec2spotmanager:poolview"

    def test_no_login(self):
        """Request without login hits the login redirect"""
        path = reverse(self.name, kwargs={'poolid': 0})
        self.assertRedirects(self.client.get(path), '/login/?next=' + path)

    def test_simpleget(self):
        """No errors are thrown in template"""
        cfg = self.create_config(name='config #1')
        pool = self.create_pool(config=cfg)
        self.client.login(username='test', password='test')
        response = self.client.get(reverse(self.name, kwargs={'poolid': pool.pk}))
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])


class PoolPricesViewTests(TestCase):
    name = "ec2spotmanager:poolprices"

    def test_no_login(self):
        """Request without login hits the login redirect"""
        path = reverse(self.name, kwargs={'poolid': 0})
        self.assertRedirects(self.client.get(path), '/login/?next=' + path)

    def test_simpleget(self):
        """No errors are thrown in template"""
        cfg = self.create_config(name='config #1',
                                 ec2_instance_types=['c4.2xlarge'])
        pool = self.create_pool(config=cfg)
        self.client.login(username='test', password='test')
        response = self.client.get(reverse(self.name, kwargs={'poolid': pool.pk}))
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])


class DeletePoolViewTests(TestCase):
    name = "ec2spotmanager:pooldel"

    def test_no_login(self):
        """Request without login hits the login redirect"""
        path = reverse(self.name, kwargs={'poolid': 0})
        self.assertRedirects(self.client.get(path), '/login/?next=' + path)

    def test_simpleget(self):
        """No errors are thrown in template"""
        cfg = self.create_config(name='config #1')
        pool = self.create_pool(config=cfg)
        self.client.login(username='test', password='test')
        response = self.client.get(reverse(self.name, kwargs={'poolid': pool.pk}))
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])


class EnablePoolViewTests(TestCase):
    name = "ec2spotmanager:poolenable"

    def test_no_login(self):
        """Request without login hits the login redirect"""
        path = reverse(self.name, kwargs={'poolid': 0})
        self.assertRedirects(self.client.get(path), '/login/?next=' + path)

    def test_simpleget(self):
        """No errors are thrown in template"""
        cfg = self.create_config(name='config #1')
        pool = self.create_pool(config=cfg)
        self.client.login(username='test', password='test')
        response = self.client.get(reverse(self.name, kwargs={'poolid': pool.pk}))
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])


class DisablePoolViewTests(TestCase):
    name = "ec2spotmanager:pooldisable"

    def test_no_login(self):
        """Request without login hits the login redirect"""
        path = reverse(self.name, kwargs={'poolid': 0})
        self.assertRedirects(self.client.get(path), '/login/?next=' + path)

    def test_simpleget(self):
        """No errors are thrown in template"""
        cfg = self.create_config(name='config #1')
        pool = self.create_pool(config=cfg)
        self.client.login(username='test', password='test')
        response = self.client.get(reverse(self.name, kwargs={'poolid': pool.pk}))
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])


class CyclePoolViewTests(TestCase):
    name = "ec2spotmanager:poolcycle"

    def test_no_login(self):
        """Request without login hits the login redirect"""
        path = reverse(self.name, kwargs={'poolid': 0})
        self.assertRedirects(self.client.get(path), '/login/?next=' + path)

    def test_simpleget(self):
        """No errors are thrown in template"""
        cfg = self.create_config(name='config #1')
        pool = self.create_pool(config=cfg)
        self.client.login(username='test', password='test')
        response = self.client.get(reverse(self.name, kwargs={'poolid': pool.pk}))
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])


class DeletePoolMessageViewTests(TestCase):
    name = "ec2spotmanager:poolmsgdel"

    def test_no_login(self):
        """Request without login hits the login redirect"""
        path = reverse(self.name, kwargs={'msgid': 0})
        self.assertRedirects(self.client.get(path), '/login/?next=' + path)

    def test_simpleget(self):
        """No errors are thrown in template"""
        cfg = self.create_config(name='config #1')
        pool = self.create_pool(config=cfg)
        msg = self.create_poolmsg(pool=pool)
        self.client.login(username='test', password='test')
        response = self.client.get(reverse(self.name, kwargs={'msgid': msg.pk}))
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])
