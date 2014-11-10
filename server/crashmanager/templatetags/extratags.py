import os
from django import template

register = template.Library()

@register.filter
def basename(value):
    return os.path.basename(value)

@register.filter
def varformat(arg, val):
    return arg % val