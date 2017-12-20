#!/usr/bin/env python
# encoding: utf-8
'''
choose_once -- Simulation handler that initially makes the cheapest choice and
               then keeps it for a lifetime. Region and instance type can be
               fixed with the corresponding parameters.

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''

# Ensure print() compatibility with Python 3
from __future__ import print_function

from .common import select_better


def run(data, sim_config, main_config):
    fixed_region = None
    fixed_instance_type = None

    if "fixed_region" in sim_config:
        fixed_region = sim_config["fixed_region"]

    if "fixed_instance_type" in sim_config:
        fixed_instance_type = sim_config["fixed_instance_type"]

    ret = select_better(data, None, fixed_region, None, fixed_instance_type, None)

    region = ret["region"]
    zone = ret["zone"]
    instance_type = ret["instance_type"]
    total_price = 0

    with open("%s.log" % sim_config["name"], mode='w') as logFileFd:
        for instance_time in data[region][zone][instance_type]:
            (_, price, _) = data[region][zone][instance_type][instance_time]
            total_price = total_price + price
            print("%s %s %s %s %s" % (region, zone, instance_type, instance_time, price), file=logFileFd)

    return total_price
