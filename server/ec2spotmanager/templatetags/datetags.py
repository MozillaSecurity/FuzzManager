from datetime import tzinfo, timedelta, datetime
from django import template

class UTC(tzinfo):
    def utcoffset(self, dt):
        return timedelta(0)
    def tzname(self, dt):
        return "UTC"
    def dst(self, dt):
        return timedelta(0)

register = template.Library()

@register.filter
def date_ago(d):
    delta = datetime.now(UTC()) - d

    days = delta.days
    hours = delta.seconds // 3600
    minutes = delta.seconds // 60 % 60

    ret = ""

    if days > 0:
        ret += "%s %s " % (days, "days" if days > 1 else "day")

    if hours > 0:
        ret += "%s %s " % (hours, "hours" if hours > 1 else "hour")

    if minutes > 0:
        ret += "%s %s " % (minutes, "minutes" if minutes > 1 else "minute")

    if not ret:
        ret = "less than a minute "

    return ret + "ago"
