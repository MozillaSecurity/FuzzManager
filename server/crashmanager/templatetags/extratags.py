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
    else:
        return ""


@register.filter
def varformat(arg, val):
    return arg % val


@register.filter
def listcsv(value):
    if value:
        return ", ".join(value)
    else:
        return ""


@register.filter
def dictcsv(value):
    if value:
        return ", ".join(["%s=%s" % x for x in value.items()])
    else:
        return ""


@register.filter
def toolcsv(value):
    if value:
        return ", ".join([x.name for x in value.all()])
    else:
        return ""
