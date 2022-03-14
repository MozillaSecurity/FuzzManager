#!/usr/bin/env python
"""
common -- Functions used by simulation handlers

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
"""

from __future__ import annotations

from typing_extensions import NotRequired, TypedDict


class RetType(TypedDict):
    """Type information for ret."""

    instance_type: NotRequired[str]
    price: NotRequired[int]
    region: NotRequired[str]
    zone: NotRequired[str]


def select_better(
    data,
    current_price: int | None = None,
    region: str | None = None,
    zone: str | None = None,
    instance_type: str | None = None,
    instance_time: int | None = None,
    indent: int = 1,
    verbose: bool = False,
) -> RetType:
    best_region = region
    best_zone = zone
    best_instance_type = instance_type
    best_price = current_price

    def print_indent(s: RetType | str) -> None:
        if verbose:
            print(f"{'*' * indent}{s}")

    if region is None:
        assert best_price is not None
        for region_name in data:
            ret = select_better(
                data,
                best_price,
                region_name,
                zone,
                instance_type,
                instance_time,
                indent + 1,
            )
            if best_price is None or best_price > ret["price"]:
                (best_region, best_zone, best_instance_type, best_price) = (
                    ret["region"],
                    ret["zone"],
                    ret["instance_type"],
                    ret["price"],
                )
            else:
                print_indent(f"Price rejected: {ret['price']} > {best_price}")
    else:
        if zone is None:
            for zone_name in data[region]:
                ret = select_better(
                    data,
                    best_price,
                    region,
                    zone_name,
                    instance_type,
                    instance_time,
                    indent + 1,
                )
                if best_price is None or best_price > ret["price"]:
                    (best_region, best_zone, best_instance_type, best_price) = (
                        ret["region"],
                        ret["zone"],
                        ret["instance_type"],
                        ret["price"],
                    )
                else:
                    print_indent(f"Price rejected: {ret['price']} > {best_price}")
        else:
            if instance_type is None:
                for instance_type_name in data[region][zone]:
                    ret = select_better(
                        data,
                        best_price,
                        region,
                        zone,
                        instance_type_name,
                        instance_time,
                        indent + 1,
                    )
                    if best_price is None or best_price > ret["price"]:
                        (best_region, best_zone, best_instance_type, best_price) = (
                            ret["region"],
                            ret["zone"],
                            ret["instance_type"],
                            ret["price"],
                        )
                    else:
                        print_indent(f"Price rejected: {ret['price']} > {best_price}")
            else:
                if instance_time is None:
                    (_, best_price, _) = list(
                        data[region][zone][instance_type].values()
                    )[0]
                else:
                    for current_time in data[region][zone][instance_type]:
                        if current_time <= instance_time:
                            (_, best_price, _) = data[region][zone][instance_type][
                                current_time
                            ]

    assert best_region is not None
    assert best_zone is not None
    assert best_instance_type is not None
    assert best_price is not None
    new_ret: RetType = {}
    new_ret["region"] = best_region
    new_ret["zone"] = best_zone
    new_ret["instance_type"] = best_instance_type
    new_ret["price"] = best_price
    print_indent(new_ret)
    return new_ret


def get_price_median(data: list[float]) -> float:
    sdata = sorted(data)
    n = len(sdata)
    if not n % 2:
        return (sdata[int(n / 2)] + sdata[int(n / 2) - 1]) / 2.0
    return sdata[int(n / 2)]
