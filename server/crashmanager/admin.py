from django.contrib import admin

from crashmanager.models import CrashEntry, Bucket, Bug, Platform, Product, OS  # @UnresolvedImport

admin.site.register(CrashEntry)
admin.site.register(Bucket)
admin.site.register(Bug)
admin.site.register(Platform)
admin.site.register(Product)
admin.site.register(OS)
