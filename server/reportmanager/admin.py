from django.contrib import admin

from reportmanager.models import (  # @UnresolvedImport
    OS,
    Bucket,
    Bug,
    Platform,
    Product,
    ReportEntry,
)

admin.site.register(ReportEntry)
admin.site.register(Bucket)
admin.site.register(Bug)
admin.site.register(Platform)
admin.site.register(Product)
admin.site.register(OS)
