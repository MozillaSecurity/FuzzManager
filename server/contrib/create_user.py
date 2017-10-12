from __future__ import print_function

import argparse
import os
import random
import string
import sys

import django


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--username', dest='username', type=str, required=True)
    parser.add_argument('--email', dest='email', type=str, required=True)
    parser.add_argument('--password', dest='password', type=str, required=False)
    parser.add_argument('--superuser', dest='superuser', action='store_true', required=False)

    args = parser.parse_args()

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.settings")

    from django.contrib.auth.models import User
    django.setup()

    username = args.username
    email = args.email
    password = ''.join(random.sample(string.letters, 20)) if args.password is None else args.password
    superuser = args.superuser

    try:
        user_obj = User.objects.get(username=args.username)
        user_obj.set_password(password)
        user_obj.save()
    except User.DoesNotExist:
        if superuser:
            User.objects.create_superuser(username, email, password)
        else:
            User.objects.create_user(username, email, password)

    print('Password: {}'.format(password))


if __name__ == '__main__':
    sys.exit(main())
