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