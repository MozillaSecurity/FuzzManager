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


def get_prices(regions, cloud_provider, instance_types=None, use_multiprocess=False):
    if use_multiprocess:
        from multiprocessing import Pool, cpu_count
        pool = Pool(cpu_count())

    try:
        results = []
        for region in regions:
            args = [region, instance_types]
            if use_multiprocess:
                results.append(pool.apply_async(cloud_provider.get_prices_per_region, args))
            else:
                results.append(cloud_provider.get_prices_per_region(*args))

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
