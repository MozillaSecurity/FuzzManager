#!/usr/bin/env python
# encoding: utf-8
'''
Price Simulator -- Tool to simulate how scheduling behavior/price strategies
                   affect the overall cost of your EC2 instances. This tool is
                   work in progress. The current TODO list includes showing
                   normalized prices (based on specified time unit and amount
                   of instances), maximum bid support and the associated uptime
                   percentage.

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
'''

# Ensure print() compatibility with Python 3
from __future__ import print_function

import boto.ec2
from collections import OrderedDict
import datetime
import importlib
import json
import os
import sys

from six.moves import configparser


now = datetime.datetime.now()


# This function must be defined at the module level so it can be pickled
# by the multiprocessing module when calling this asynchronously.
def get_spot_price_per_region(region_name, start_time, end_time, aws_key_id, aws_secret_key, instance_type):
    '''Gets spot prices of the specified region and instance type'''

    print("Region %s Instance Type %s Start %s End %s" % (region_name, instance_type, start_time.isoformat(),
                                                          end_time.isoformat()))
    r = None

    while True:
        try:
            region = boto.ec2.connect_to_region(region_name,
                                                aws_access_key_id=aws_key_id,
                                                aws_secret_access_key=aws_secret_key
                                                )

            if not region:
                raise RuntimeError("Invalid region: %s" % region_name)

            r = region.get_spot_price_history(start_time=start_time.isoformat(),
                                              end_time=end_time.isoformat(),
                                              instance_type=instance_type,
                                              product_description="Linux/UNIX"
                                              )  # TODO: Make configurable
            break
        except Exception:
            print("Caught exception, retrying")
            pass

    return r


def get_spot_prices(regions, start_time, end_time, aws_key_id, aws_secret_key, instance_types, prices,
                    use_multiprocess=False):
    if use_multiprocess:
        from multiprocessing import Pool, cpu_count
        pool = Pool(cpu_count())

    results = []
    for instance_type in instance_types:
        for region in regions:
            if use_multiprocess:
                f = pool.apply_async(get_spot_price_per_region, [region, start_time, end_time, aws_key_id,
                                                                 aws_secret_key, instance_type])
            else:
                f = get_spot_price_per_region(region, start_time, end_time, aws_key_id, aws_secret_key, instance_type)
            results.append(f)

    for result in results:
        if use_multiprocess:
            result = result.get()
        for entry in result:
            if entry.region.name not in prices:
                prices[entry.region.name] = {}

            zone = entry.availability_zone

            if zone not in prices[entry.region.name]:
                prices[entry.region.name][zone] = {}

            if entry.instance_type not in prices[entry.region.name][zone]:
                prices[entry.region.name][zone][entry.instance_type] = OrderedDict()

            if not start_time.isoformat() in prices[entry.region.name][zone][entry.instance_type]:
                prices[entry.region.name][zone][entry.instance_type][start_time.isoformat()] = [end_time.isoformat(),
                                                                                                entry.price, 1]
            else:
                cur = prices[entry.region.name][zone][entry.instance_type][start_time.isoformat()]

                mean_price = float((cur[1] * cur[2]) + entry.price) / float(cur[2] + 1)

                prices[entry.region.name][zone][entry.instance_type][start_time.isoformat()] = [end_time.isoformat(),
                                                                                                mean_price, cur[2] + 1]


class ConfigurationFile():
    def __init__(self, configFile):
        self.simulations = OrderedDict()
        self.main = {}
        if configFile:
            self.parser = configparser.ConfigParser()

            # Make sure keys are kept case-sensitive
            self.parser.optionxform = str

            self.parser.read([configFile])

            sections = self.parser.sections()
            for section in sections:
                sectionMap = self.getSectionMap(section)

                if section.lower() == "main":
                    mandatoryFields = ["aws_access_key_id", "aws_secret_key", "regions", "interval", "instance_types",
                                       "cache_file"]

                    for mandatoryField in mandatoryFields:
                        if mandatoryField not in sectionMap:
                            print("Error: Main configuration is missing mandatory field '%s'." % mandatoryField)
                            return

                    self.main = sectionMap
                else:
                    if "handler" not in sectionMap:
                        print("Warning: Simulation '%s' has no handler set, ignoring..." % section)
                        continue

                    # Store the name in the section map as well
                    sectionMap["name"] = section

                    self.simulations[section] = sectionMap

    def getSectionMap(self, section):
        ret = OrderedDict()
        try:
            options = self.parser.options(section)
        except configparser.NoSectionError:
            return {}
        for o in options:
            ret[o] = self.parser.get(section, o)
        return ret


def main():
    '''Command line options.'''

    # setup argparser
    # parser = argparse.ArgumentParser()
    # parser.add_argument('rargs', nargs=argparse.REMAINDER)

    # process options
    # opts = parser.parse_args()

    configFile = ConfigurationFile(sys.argv[1])

    if not configFile.main:
        sys.exit(1)

    if not configFile.simulations:
        print("Error: No simulations configured, exiting...")
        sys.exit(1)

    results = OrderedDict()

    cacheFile = configFile.main["cache_file"]
    regions = configFile.main["regions"].split(",")
    instance_types = configFile.main["instance_types"].split(",")
    interval = int(configFile.main["interval"])
    aws_access_key_id = configFile.main["aws_access_key_id"]
    aws_secret_key = configFile.main["aws_secret_key"]

    for (simulation_name, simulation) in configFile.simulations.items():
        sim_module = importlib.import_module("simulations.%s" % simulation["handler"])

        print("Performing simulation '%s' ..." % simulation_name)

        priceData = {}

        if os.path.isfile(cacheFile):
            with open(cacheFile, mode='r') as cacheFd:
                priceData = json.load(cacheFd, object_pairs_hook=OrderedDict)
        else:
            for hour in range(interval - 1, -1, -1):
                print("Obtaining hour %s" % (hour + 1))
                stop = now - datetime.timedelta(hours=hour)
                start = now - datetime.timedelta(hours=hour + 1)

                get_spot_prices(regions, start, stop, aws_access_key_id, aws_secret_key, instance_types, priceData,
                                use_multiprocess=False)

            with open(cacheFile, mode='w') as cacheFd:
                json.dump(priceData, cacheFd)

        total_price = sim_module.run(priceData, simulation, configFile.main)
        results[simulation_name] = total_price

    print("")

    col_len = None

    for simulation in results:
        print("Simulation %s (total price): %s" % (simulation, results[simulation]))

        if col_len is None or col_len < len(simulation):
            col_len = len(simulation)

    col_len += 1

    print("")

    sys.stdout.write(" " * col_len)
    for simulation in results:
        sys.stdout.write(simulation)
        # sys.stdout.write(" "*(col_len - len(simulation)))
        sys.stdout.write("  ")
    sys.stdout.write("\n")

    for simulation_a in results:
        sys.stdout.write(simulation_a)
        sys.stdout.write(" " * (col_len - len(simulation_a)))
        for simulation_b in results:
            price_a = results[simulation_a]
            price_b = results[simulation_b]

            p = "%.2f %%" % (100 - (price_a / price_b) * 100)

            sys.stdout.write(p)
            sys.stdout.write(" " * (len(simulation_b) - len(p) + 2))
        sys.stdout.write("\n")


if __name__ == "__main__":
    sys.exit(main())
