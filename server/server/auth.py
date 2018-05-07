# This is code for Mozilla's 2FA using OID. If you have your own OID provider,
# you can probably use similar code to get 2FA for your FuzzManager instance.

import unicodedata

from django.conf import settings
from mozilla_django_oidc.auth import OIDCAuthenticationBackend # noqa


def generate_username(email):
    # Using Python 3 and Django 1.11, usernames can contain alphanumeric
    # (ascii and unicode), _, @, +, . and - characters. So we normalize
    # it and slice at 150 characters.
    return unicodedata.normalize('NFKC', email)[:150]


class FMOIDCAB(OIDCAuthenticationBackend):
    def verify_claims(self, claims):
        verified = super(FMOIDCAB, self).verify_claims(claims)

        if not verified:
            return False

        email = claims.get('email', None)
        return email in settings.OID_ALLOWED_USERS
