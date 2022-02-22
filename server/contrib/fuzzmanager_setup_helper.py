import os
import random
import string
import subprocess
import sys

import django


def create_fuzzmanager():
    # This is a throw away password, that is soon reset to the auth_token for
    # fuzzmanager
    password = "".join(random.sample(string.letters, 20))
    print("[+] Creating fuzzmanager user account.")
    from django.contrib.auth.models import User

    User.objects.create_superuser("fuzzmanager", "fuzzmanager@example.com", password)
    try:
        print("[+] Super user fuzzmanager created")
        print("[+] Obtaining auth token for fuzzmanager")
        auth_token = subprocess.check_output(
            ["python", "manage.py", "get_auth_token", "fuzzmanager"]
        )
        auth_token = auth_token.strip()
        print("[+] Creating .fuzzmanagerconf")
        home = os.path.expanduser("~")
        sigdir = input(
            f"Enter the the path to store fuzzmanager signatures. {home}/signatures "
            "would be a good choice.\n"
        )
        serverhost = input(
            "Enter the IP Address for the fuzzmanager host or to accept 127.0.0.1, "
            "press ENTER\n"
        )
        if not serverhost:
            serverhost = "127.0.0.1"
        serverport = input(
            "Enter the TCP port for fuzzmanager or to accept 8000, press ENTER\n"
        )
        if not serverport:
            serverport = "8000"
        serverproto = input(
            "Type https to use https protocol or to accept http, press ENTER\n"
        )
        if not serverproto:
            serverproto = "http"

        with open(".fuzzmanagerconf", "w") as f:
            f.write("[Main]\n")
            f.write(f"sigdir = {sigdir}\n")
            f.write(f"serverhost = {serverhost}\n")
            f.write(f"serverport = {serverport}\n")
            f.write(f"serverproto = {serverproto}\n")
            f.write(f"serverauthtoken = {auth_token}\n")
            f.write("tool = jsfunfuzz\n")

        with open(".fuzzmanagerconf") as f:
            print(f.read())

        user_obj = User.objects.get(username="fuzzmanager")
        user_obj.set_password(auth_token)
        user_obj.save()
        print(
            "[+] The fuzzmanager account password has been set to the auth_token "
            f"{auth_token}"
        )
        output = subprocess.check_output(
            ["htpasswd", "-cb", ".htpasswd", "fuzzmanager", auth_token]
        )
        print(output)
        print(
            "[+] .htpasswd created for apache basic authentication with the "
            f"fuzzmanager user password set to {auth_token}"
        )
        print(
            "Update the AuthUserFile path/to/.htpasswd line as shown in "
            "examples/apache2/default.vhost to point to this file"
        )
    except User.DoesNotExist:
        print("Something went wrong creating the fuzzmanager account")


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "server.settings")
    from django.contrib.auth.models import User

    django.setup()

    try:
        user_obj = User.objects.get(username="fuzzmanager")
    except django.db.utils.OperationalError:
        print("[+] Performing python manage.py migrate")
        output = subprocess.check_output(["python", "manage.py", "migrate"])
        print(output)
        create_fuzzmanager()
    except User.DoesNotExist:
        create_fuzzmanager()

    while True:
        username = input("Please enter a user account to create, or ENTER to quit\n")
        if not username:
            break
        password = input(f"Please enter a password for {username}\n")
        email = input(f"Please enter an email address for {username}\n")
        su = input(f"Is {username} a super user account? (y/n)")

        if su == "y":
            superuser = True
        else:
            superuser = False

        try:
            user_obj = User.objects.get(username=username)
            user_obj.set_password(password)
            user_obj.save()
        except User.DoesNotExist:
            if superuser:
                User.objects.create_superuser(username, email, password)
            else:
                User.objects.create_user(username, email, password)

        output = subprocess.check_output(
            ["htpasswd", "-b", ".htpasswd", username, password]
        )
        print(output)


if __name__ == "__main__":
    sys.exit(main())
