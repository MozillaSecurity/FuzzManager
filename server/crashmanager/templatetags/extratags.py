from __future__ import annotations

import json
import os

from django import template

register = template.Library()


@register.filter
def basename(value: str) -> str:
    return os.path.basename(value)


@register.filter
def linejoin(value: list[str]) -> str:
    if value:
        return "\n".join(value)
    else:
        return ""


@register.filter
def varformat(arg: int, val: int) -> int:
    return arg % val


@register.filter
def listcsv(value: list[str]) -> str:
    if value:
        return ", ".join(value)
    else:
        return ""


@register.filter
def dictcsv(value: dict[str, object]) -> str:
    if value:
        return ", ".join("%s=%s" % x for x in value.items())
    else:
        return ""


@register.filter
def jsonparse(value: str):
    if value:
        return json.loads(value)
    else:
        return ""
