from django.shortcuts import redirect
from django.contrib.auth.views import login as django_login
from django.conf import settings


def index(request):
    return redirect('crashmanager:crashes')


def login(request):
    if settings.USE_OIDC:
        return redirect('oidc_authentication_init')
    return django_login(request)
