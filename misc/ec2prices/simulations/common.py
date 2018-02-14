#!/usr/bin/env python
# encoding: utf-8
'''
common -- Functions used by simulation handlers

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''
from __future__ import print_function


def select_better(data, current_price=None, region=None, zone=None, instance_type=None, instance_time=None, indent=1,
                  verbose=False):
    best_region = region
    best_zone = zone
    best_instance_type = instance_type
    best_price = current_price

    def print_indent(s):
        if verbose:
            print("%s%s" % ("*" * indent, s))

    if region is None:
        for region_name in data:
            ret = select_better(data, best_price, region_name, zone, instance_type, instance_time, indent + 1)
            if (best_price is None or best_price > ret["price"]):
                (best_region, best_zone, best_instance_type, best_price) = (ret["region"], ret["zone"],
                                                                            ret["instance_type"], ret["price"])
            else:
                print_indent("Price rejected: %s > %s" % (ret["price"], best_price))
    else:
        if zone is None:
            for zone_name in data[region]:
                ret = select_better(data, best_price, region, zone_name, instance_type, instance_time, indent + 1)
                if (best_price is None or best_price > ret["price"]):
                    (best_region, best_zone, best_instance_type, best_price) = (ret["region"], ret["zone"],
                                                                                ret["instance_type"], ret["price"])
                else:
                    print_indent("Price rejected: %s > %s" % (ret["price"], best_price))
        else:
            if instance_type is None:
                for instance_type_name in data[region][zone]:
                    ret = select_better(data, best_price, region, zone, instance_type_name, instance_time, indent + 1)
                    if (best_price is None or best_price > ret["price"]):
                        (best_region, best_zone, best_instance_type, best_price) = (ret["region"], ret["zone"],
                                                                                    ret["instance_type"], ret["price"])
                    else:
                        print_indent("Price rejected: %s > %s" % (ret["price"], best_price))
            else:
                if instance_time is None:
                    (_, best_price, _) = list(data[region][zone][instance_type].values())[0]
                else:
                    for current_time in data[region][zone][instance_type]:
                        if current_time <= instance_time:
                            (_, best_price, _) = data[region][zone][instance_type][current_time]

    new_ret = {}
    new_ret["region"] = best_region
    new_ret["zone"] = best_zone
    new_ret["instance_type"] = best_instance_type
    new_ret["price"] = best_price
    print_indent(new_ret)
    return new_ret


def get_price_median(data):
    sdata = sorted(data)
    n = len(sdata)
    if not n % 2:
        return (sdata[n / 2] + sdata[n / 2 - 1]) / 2.0
    return sdata[n / 2]
