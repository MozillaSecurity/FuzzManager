#!/usr/bin/env python
# encoding: utf-8
'''
Prices -- Various methods for accessing price history on EC2

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''
import datetime

import boto.ec2
from django.utils import timezone


# Blacklist zones that currently don't allow subnets to be set on them
# until we found a better way to deal with this situation.
zone_blacklist = ["us-east-1a", "us-east-1f"]


# This function must be defined at the module level so it can be pickled
# by the multiprocessing module when calling this asynchronously.
def get_spot_price_per_region(region_name, aws_key_id, aws_secret_key, instance_type):
    '''Gets spot prices of the specified region and instance type'''
    now = timezone.now()
    start = now - datetime.timedelta(hours=6)
    region = boto.ec2.connect_to_region(region_name,
                                        aws_access_key_id=aws_key_id,
                                        aws_secret_access_key=aws_secret_key
                                        )

    if not region:
        raise RuntimeError("Invalid region: %s" % region_name)

    r = region.get_spot_price_history(start_time=start.isoformat(),
                                      instance_type=instance_type,
                                      product_description="Linux/UNIX"
                                      )  # TODO: Make configurable
    return r


def get_spot_prices(regions, aws_key_id, aws_secret_key, instance_type, use_multiprocess=False):
    if use_multiprocess:
        from multiprocessing import Pool, cpu_count
        pool = Pool(cpu_count())

    results = []
    for region in regions:
        if use_multiprocess:
            f = pool.apply_async(get_spot_price_per_region, [region, aws_key_id, aws_secret_key, instance_type])
        else:
            f = get_spot_price_per_region(region, aws_key_id, aws_secret_key, instance_type)
        results.append(f)

    prices = {}
    for result in results:
        if use_multiprocess:
            result = result.get()
        for entry in result:
            if entry.region.name not in prices:
                prices[entry.region.name] = {}

            zone = entry.availability_zone

            if zone in zone_blacklist:
                continue

            if zone not in prices[entry.region.name]:
                prices[entry.region.name][zone] = []

            prices[entry.region.name][zone].append(entry.price)

    return prices


def get_price_median(data):
    sdata = sorted(data)
    n = len(sdata)
    if not n % 2:
        return (sdata[n // 2] + sdata[n // 2 - 1]) / 2.0
    return sdata[n // 2]
