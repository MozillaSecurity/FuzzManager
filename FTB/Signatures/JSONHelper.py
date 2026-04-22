"""
JSONHelper

Various functions around JSON encoding/decoding

@author:     Christian Holler (:decoder)

@license:

This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.

@contact:    choller@mozilla.com
"""

import numbers
from collections.abc import Mapping
from typing import Any


def getArrayChecked(
    obj: Mapping[str, Any], key: str, mandatory: bool = False
) -> list[Any] | None:
    """
    Retrieve a list from the given object using the given key

    @type obj: map
    @param obj: Source object

    @type key: string
    @param key: Key to retrieve from obj

    @type mandatory: bool
    @param mandatory: If True, throws an exception if the key is not found

    @rtype: list
    @return: List retrieved from object
    """
    return __getTypeChecked(obj, key, [list], mandatory)  # type: ignore[no-any-return]


def getStringChecked(
    obj: Mapping[str, Any], key: str, mandatory: bool = False
) -> str | None:
    """
    Retrieve a string from the given object using the given key

    @type obj: map
    @param obj: Source object

    @type key: string
    @param key: Key to retrieve from obj

    @type mandatory: bool
    @param mandatory: If True, throws an exception if the key is not found

    @rtype: string
    @return: String retrieved from object
    """
    return __getTypeChecked(obj, key, [str], mandatory)  # type: ignore[no-any-return]


def getNumberChecked(
    obj: Mapping[str, Any], key: str, mandatory: bool = False
) -> int | None:
    """
    Retrieve an integer from the given object using the given key

    @type obj: map
    @param obj: Source object

    @type key: string
    @param key: Key to retrieve from obj

    @type mandatory: bool
    @param mandatory: If True, throws an exception if the key is not found

    @rtype: int
    @return: Number retrieved from object
    """
    return __getTypeChecked(obj, key, [numbers.Integral], mandatory)  # type: ignore[no-any-return]


def getObjectOrStringChecked(
    obj: Mapping[str, Any], key: str, mandatory: bool = False
) -> str | dict[str, Any] | None:
    """
    Retrieve an object or string from the given object using the given key

    @type obj: map
    @param obj: Source object

    @type key: string
    @param key: Key to retrieve from obj

    @type mandatory: bool
    @param mandatory: If True, throws an exception if the key is not found

    @rtype: string or dict
    @return: String/Object object retrieved from object
    """
    return __getTypeChecked(obj, key, [str, dict], mandatory)  # type: ignore[no-any-return]


def getNumberOrStringChecked(
    obj: Mapping[str, Any], key: str, mandatory: bool = False
) -> str | int | None:
    """
    Retrieve a number or string from the given object using the given key

    @type obj: map
    @param obj: Source object

    @type key: string
    @param key: Key to retrieve from obj

    @type mandatory: bool
    @param mandatory: If True, throws an exception if the key is not found

    @rtype: string or number
    @return: String/Number object retrieved from object
    """
    return __getTypeChecked(obj, key, [str, numbers.Integral], mandatory)  # type: ignore[no-any-return]


def __getTypeChecked(
    obj: Mapping[str, Any],
    key: str,
    valTypes: list[type],
    mandatory: bool = False,
) -> Any:
    if key not in obj:
        if mandatory:
            raise RuntimeError(f'Expected key "{key}" in object')
        return None

    val = obj[key]

    if isinstance(val, tuple(valTypes)):
        return val

    raise RuntimeError(
        'Expected any of types "{}" for key "{}" but got type {}'.format(
            ", ".join([str(i) for i in valTypes]), key, type(val)
        )
    )
