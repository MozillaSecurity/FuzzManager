'''
Tests for Configuration views.

@author:     Jesse Schwartzentruber (:truber)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
'''

import decimal
import json
import logging

import requests
from django.core.urlresolvers import reverse

from . import TestCase
from ..models import PoolConfiguration


log = logging.getLogger("fm.ec2spotmanager.tests.configs")  # pylint: disable=invalid-name


class ConfigsViewTests(TestCase):
    name = "ec2spotmanager:configs"

    def test_no_login(self):
        """Request without login hits the login redirect"""
        path = reverse(self.name)
        response = self.client.get(path)
        log.debug(response)
        self.assertRedirects(response, '/login/?next=' + path)

    def test_no_configs(self):
        """If no configs in db, an appropriate message is shown."""
        self.client.login(username='test', password='test')
        response = self.client.get(reverse(self.name))
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])
        configtree = response.context['roots']
        self.assertEqual(len(configtree), 0)  # 0 configs

    def test_config(self):
        """Create config and see that it is shown."""
        self.client.login(username='test', password='test')
        config = self.create_config("config #1")
        response = self.client.get(reverse(self.name))
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])
        configtree = response.context['roots']
        self.assertEqual(len(configtree), 1)  # 1 config
        self.assertEqual(set(configtree), {config})  # same config
        self.assertEqual(len(configtree[0].children), 0)
        self.assertContains(response, "config #1")

    def test_configs(self):
        """Create configs and see that they are shown."""
        self.client.login(username='test', password='test')
        configs = (self.create_config("config #1"),
                   self.create_config("config #2"))
        response = self.client.get(reverse(self.name))
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])
        configtree = response.context['roots']
        self.assertEqual(len(configtree), 2)  # 2 configs
        self.assertEqual(set(configtree), set(configs))  # same configs
        self.assertEqual(len(configtree[0].children), 0)
        self.assertEqual(len(configtree[1].children), 0)
        self.assertContains(response, "config #1")
        self.assertContains(response, "config #2")

    def test_config_tree(self):
        """Create nested configs and see that they are shown."""
        self.client.login(username='test', password='test')
        config1 = self.create_config("config #1")
        config2 = self.create_config("config #2", parent=config1)
        config3 = self.create_config("config #3")
        response = self.client.get(reverse(self.name))
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])
        configtree = response.context['roots']
        self.assertEqual(len(configtree), 2)  # 2 top-level configs
        self.assertEqual(set(configtree), {config1, config3})
        seen1 = seen3 = False
        for cfg in configtree:
            if cfg == config1:
                self.assertFalse(seen1)
                seen1 = True
                self.assertEqual(len(cfg.children), 1)
                self.assertEqual(set(cfg.children), {config2})
            elif cfg == config3:
                self.assertFalse(seen3)
                seen3 = True
                self.assertEqual(len(cfg.children), 0)
            else:
                raise Exception("unexpected configuration: %s" % cfg.name)
        self.assertTrue(seen1)
        self.assertTrue(seen3)
        self.assertContains(response, "config #1")
        self.assertContains(response, "config #2")
        self.assertContains(response, "config #3")


class CreateConfigViewTests(TestCase):
    name = "ec2spotmanager:configcreate"

    def test_no_login(self):
        """Request without login hits the login redirect"""
        path = reverse(self.name)
        response = self.client.get(path)
        log.debug(response)
        self.assertRedirects(response, '/login/?next=' + path)

    def test_create_form(self):
        """Config creation form should be shown"""
        self.client.login(username='test', password='test')
        response = self.client.get(reverse(self.name))
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])
        self.assertContains(response, "Create Configuration")
        self.assertContains(response, 'name="name"')
        self.assertContains(response, 'name="size"')
        self.assertContains(response, 'name="cycle_interval"')
        self.assertContains(response, 'name="aws_access_key_id"')

    def test_create(self):
        """Config created via form should be added to db"""
        self.client.login(username='test', password='test')
        response = self.client.post(reverse(self.name), {'parent': '-1',
                                                         'name': 'config #1',
                                                         'size': '1',
                                                         'cycle_interval': '1',  # activate tsmith mode
                                                         'aws_access_key_id': 'deadbeef',
                                                         'aws_secret_access_key': 'n0b0deee',
                                                         'ec2_key_name': 'key #1',
                                                         'ec2_security_groups': 'group #1',
                                                         'ec2_instance_types': 'machine #1',
                                                         'ec2_image_name': 'ami #1',
                                                         'ec2_userdata': 'lorem ipsum',
                                                         'ec2_userdata_macros': 'yup=123,nope=456',
                                                         'ec2_allowed_regions': 'nowhere',
                                                         'ec2_max_price': '0.01',
                                                         'ec2_tags': 'good=true, bad=false',
                                                         'ec2_raw_config': 'hello=world'})
        log.debug(response)
        cfg = PoolConfiguration.objects.get(name='config #1')
        self.assertIsNone(cfg.parent)
        self.assertEqual(cfg.size, 1)
        self.assertEqual(cfg.cycle_interval, 1)
        self.assertEqual(cfg.aws_access_key_id, 'deadbeef')
        self.assertEqual(cfg.aws_secret_access_key, 'n0b0deee')
        self.assertEqual(cfg.ec2_key_name, 'key #1')
        self.assertEqual(cfg.ec2_security_groups, json.dumps(['group #1']))
        self.assertEqual(cfg.ec2_instance_types, json.dumps(['machine #1']))
        self.assertEqual(cfg.ec2_image_name, 'ami #1')
        self.assertEqual(cfg.ec2_userdata_file.read(), b'lorem ipsum')
        self.assertEqual(cfg.ec2_userdata_macros, json.dumps({'yup': '123', 'nope': '456'}))
        self.assertEqual(cfg.ec2_allowed_regions, json.dumps(['nowhere']))
        self.assertEqual(cfg.ec2_max_price, decimal.Decimal('0.01'))
        self.assertEqual(cfg.ec2_tags, json.dumps({'good': 'true', 'bad': 'false'}))
        self.assertEqual(cfg.ec2_raw_config, json.dumps({'hello': 'world'}))
        self.assertRedirects(response, reverse('ec2spotmanager:configview', kwargs={'configid': cfg.pk}))

    def test_clone(self):
        """Creation form should contain source data"""
        self.client.login(username='test', password='test')
        cfg = self.create_config(name='config #1',
                                 size=1234567,
                                 cycle_interval=7654321,
                                 aws_access_key_id='deadbeef',
                                 aws_secret_access_key='n0b0deee',
                                 ec2_key_name='key #1',
                                 ec2_security_groups=['group #1'],
                                 ec2_instance_types=['machine #1'],
                                 ec2_image_name='ami #1',
                                 ec2_userdata_macros={'yup': '123', 'nope': '456'},
                                 ec2_allowed_regions=['nowhere'],
                                 ec2_max_price='0.01',
                                 ec2_tags={'good': 'true', 'bad': 'false'},
                                 ec2_raw_config={'hello': 'world'})
        response = self.client.get(reverse(self.name), {'clone': cfg.pk})
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])
        self.assertContains(response, "Clone Configuration")
        self.assertContains(response, 'config #1 (Cloned)')
        self.assertContains(response, '1234567')
        self.assertContains(response, '7654321')
        self.assertContains(response, 'deadbeef')
        self.assertContains(response, 'n0b0deee')
        self.assertContains(response, 'key #1')
        self.assertContains(response, 'group #1')
        self.assertContains(response, 'machine #1')
        self.assertContains(response, 'ami #1')
        self.assertContains(response, 'yup=123')
        self.assertContains(response, 'nope=456')
        self.assertContains(response, 'nowhere')
        self.assertContains(response, '0.01')
        self.assertContains(response, 'bad=false')
        self.assertContains(response, 'good=true')
        self.assertContains(response, 'hello=world')


class ViewConfigViewTests(TestCase):
    name = "ec2spotmanager:configview"

    def test_no_login(self):
        """Request without login hits the login redirect"""
        path = reverse(self.name, kwargs={'configid': 0})
        self.assertRedirects(self.client.get(path), '/login/?next=' + path)

    def test_config(self):
        """Create a config and view it"""
        cfg = self.create_config(name='config #1',
                                 size=1234567,
                                 cycle_interval=7654321,
                                 aws_access_key_id='deadbeef',
                                 aws_secret_access_key='n0b0deee',
                                 ec2_key_name='key #1',
                                 ec2_security_groups=['group #1'],
                                 ec2_instance_types=['machine #1'],
                                 ec2_image_name='ami #1',
                                 ec2_userdata_macros={'yup': '123', 'nope': '456'},
                                 ec2_allowed_regions=['nowhere'],
                                 ec2_max_price='0.01',
                                 ec2_tags={'good': 'true', 'bad': 'false'},
                                 ec2_raw_config={'hello': 'world'})
        self.client.login(username='test', password='test')
        response = self.client.get(reverse(self.name, kwargs={'configid': cfg.pk}))
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])
        self.assertContains(response, 'config #1')
        self.assertContains(response, '1234567')
        self.assertContains(response, '7654321')
        self.assertContains(response, 'deadbeef')
        self.assertContains(response, 'n0b0deee')
        self.assertContains(response, 'key #1')
        self.assertContains(response, 'group #1')
        self.assertContains(response, 'machine #1')
        self.assertContains(response, 'ami #1')
        self.assertContains(response, '&quot;yup&quot;: &quot;123&quot;')
        self.assertContains(response, '&quot;nope&quot;: &quot;456&quot;')
        self.assertContains(response, 'nowhere')
        self.assertContains(response, '0.01')
        self.assertContains(response, '&quot;bad&quot;: &quot;false&quot;')
        self.assertContains(response, '&quot;good&quot;: &quot;true&quot;')
        self.assertContains(response, '&quot;hello&quot;: &quot;world&quot;')


class EditConfigViewTests(TestCase):
    name = "ec2spotmanager:configedit"

    def test_no_login(self):
        """Request without login hits the login redirect"""
        path = reverse(self.name, kwargs={'configid': 0})
        response = self.client.get(path)
        log.debug(response)
        self.assertRedirects(response, '/login/?next=' + path)

    def test_edit(self):
        """Edit an existing config"""
        cfg = self.create_config(name='config #1',
                                 size=1234567,
                                 cycle_interval=7654321,
                                 aws_access_key_id='deadbeef',
                                 aws_secret_access_key='n0b0deee',
                                 ec2_key_name='key #1',
                                 ec2_security_groups=['group #1'],
                                 ec2_instance_types=['machine #1'],
                                 ec2_image_name='ami #1',
                                 ec2_userdata_macros={'yup': '123', 'nope': '456'},
                                 ec2_allowed_regions=['nowhere'],
                                 ec2_max_price='0.01',
                                 ec2_tags={'good': 'true', 'bad': 'false'},
                                 ec2_raw_config={'hello': 'world'})
        self.client.login(username='test', password='test')
        response = self.client.get(reverse(self.name, kwargs={'configid': cfg.pk}))
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])
        self.assertContains(response, "Edit Configuration")
        self.assertContains(response, 'config #1')
        self.assertContains(response, '1234567')
        self.assertContains(response, '7654321')
        self.assertContains(response, 'deadbeef')
        self.assertContains(response, 'n0b0deee')
        self.assertContains(response, 'key #1')
        self.assertContains(response, 'group #1')
        self.assertContains(response, 'machine #1')
        self.assertContains(response, 'ami #1')
        self.assertContains(response, 'yup=123')
        self.assertContains(response, 'nope=456')
        self.assertContains(response, 'nowhere')
        self.assertContains(response, '0.01')
        self.assertContains(response, 'bad=false')
        self.assertContains(response, 'good=true')
        self.assertContains(response, 'hello=world')


class DelConfigViewTests(TestCase):
    name = "ec2spotmanager:configdel"

    def test_no_login(self):
        """Request without login hits the login redirect"""
        path = reverse(self.name, kwargs={'configid': 0})
        response = self.client.get(path)
        log.debug(response)
        self.assertRedirects(response, '/login/?next=' + path)

    def test_delete(self):
        """Delete an existing config"""
        cfg = self.create_config(name='config #1')
        self.client.login(username='test', password='test')
        response = self.client.post(reverse(self.name, kwargs={'configid': cfg.pk}))
        log.debug(response)
        self.assertRedirects(response, reverse('ec2spotmanager:configs'))
        self.assertEqual(PoolConfiguration.objects.count(), 0)

    def test_simpleget(self):
        """No errors are thrown in template"""
        cfg = self.create_config(name='config #1')
        self.client.login(username='test', password='test')
        response = self.client.get(reverse(self.name, kwargs={'configid': cfg.pk}))
        log.debug(response)
        self.assertEqual(response.status_code, requests.codes['ok'])
