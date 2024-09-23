import json
import os

from django import template

register = template.Library()


@register.filter
def basename(value):
    return os.path.basename(value)


@register.filter
def linejoin(value):
    if value:
        return "\n".join(value)
    return ""


@register.filter
def varformat(arg, val):
    return arg % val


@register.filter
def listcsv(value):
    if value:
        return ", ".join(value)
    return ""


@register.filter
def dictcsv(value):
    if value:
        return ", ".join(f"{k}={v}" for (k, v) in value.items())
    return ""


@register.filter
def jsonparse(value):
    if value:
        return json.loads(value)
    return ""


@register.filter
def jsonpp(value):
    return json.dumps(value, indent=2, sort_keys=True)
