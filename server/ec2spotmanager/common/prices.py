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

import botocore
import boto3
from django.utils import timezone


# Blacklist zones that currently don't allow subnets to be set on them
# until we found a better way to deal with this situation.
zone_blacklist = ["us-east-1a", "us-east-1f"]


# This function must be defined at the module level so it can be pickled
# by the multiprocessing module when calling this asynchronously.
def get_spot_price_per_region(region_name, aws_key_id, aws_secret_key, instance_types=None):
    '''Gets spot prices of the specified region and instance type'''
    prices = {}  # {instance-type: region: {az: [prices]}}}

    now = timezone.now()

    # TODO: Make configurable
    spot_history_args = {
        'Filters': [{'Name': 'product-description', 'Values': ['Linux/UNIX']}],
        'StartTime': now - datetime.timedelta(hours=6)
    }
    if instance_types is not None:
        spot_history_args['InstanceTypes'] = instance_types

    cli = boto3.client('ec2', region_name=region_name, aws_access_key_id=aws_key_id,
                       aws_secret_access_key=aws_secret_key)
    paginator = cli.get_paginator('describe_spot_price_history')
    try:
        for result in paginator.paginate(**spot_history_args):
            for price in result['SpotPriceHistory']:
                if price['AvailabilityZone'] in zone_blacklist:
                    continue
                (prices
                 .setdefault(price['InstanceType'], {})
                 .setdefault(region_name, {})
                 .setdefault(price['AvailabilityZone'], [])
                 .append(float(price['SpotPrice'])))
    except botocore.exceptions.EndpointConnectionError as exc:
        raise RuntimeError("Boto connection error: %s" % (exc,))

    return prices


def get_spot_prices(regions, aws_key_id, aws_secret_key, instance_types=None, use_multiprocess=False):
    if use_multiprocess:
        from multiprocessing import Pool, cpu_count
        pool = Pool(cpu_count())

    try:
        results = []
        for region in regions:
            if use_multiprocess:
                results.append(pool.apply_async(get_spot_price_per_region, [region, aws_key_id, aws_secret_key, instance_types]))
            else:
                results.append(get_spot_price_per_region(region, aws_key_id, aws_secret_key, instance_types))

        prices = {}
        for result in results:
            if use_multiprocess:
                result = result.get()
            for instance_type in result:
                prices.setdefault(instance_type, {})
                prices[instance_type].update(result[instance_type])
    finally:
        if use_multiprocess:
            pool.close()
            pool.join()

    return prices


def get_price_median(data):
    sdata = sorted(data)
    n = len(sdata)
    if not n % 2:
        return (sdata[n // 2] + sdata[n // 2 - 1]) / 2.0
    return sdata[n // 2]
