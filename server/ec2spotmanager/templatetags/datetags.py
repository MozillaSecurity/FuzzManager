import datetime
from django import template

register = template.Library()

@register.filter
def date_ago(d):
    delta = datetime.datetime.now() - d

    ret = ""

    if delta.days > 0:
        ret += "%s %s " % (delta.days, "days" if delta.days > 1 else "day")

    if delta.hours > 0:
        ret += "%s %s " % (delta.hours, "hours" if delta.hours > 1 else "hour")

    if delta.minutes > 0:
        ret += "%s %s " % (delta.minutes, "minutes" if delta.minutes > 1 else "minute")

    if not ret:
        ret = "less than a minute "

    return ret + "ago"
