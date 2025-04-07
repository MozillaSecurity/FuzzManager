from django.core.management.base import BaseCommand, CommandError
from rest_framework.authtoken.models import Token

from server.models import TokenIPRestriction


class Command(BaseCommand):
    help = "Manage IP restrictions for authentication tokens"

    def add_arguments(self, parser):
        parser.add_argument("token", help="Full token key to manage")

        # IP restriction actions
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            "--add", help="Add an IP restriction (CIDR notation, e.g., 192.168.1.0/24)"
        )
        group.add_argument("--remove", help="Remove an IP restriction (CIDR notation)")
        group.add_argument(
            "--reset",
            action="store_true",
            help="Reset to default open policy (0.0.0.0/0 and ::/0)",
        )
        group.add_argument(
            "--list",
            action="store_true",
            help="List current IP restrictions for this token",
        )

        # Force option for potentially dangerous operations
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force the operation without confirmation",
        )

    def handle(self, *args, **options):
        token_key = options["token"]

        # Find token by exact key
        try:
            token = Token.objects.get(key=token_key)
        except Token.DoesNotExist:
            raise CommandError(f"Token with key '{token_key}' not found")

        self.stdout.write(f"Found token: {token.key} (User: {token.user.username})")

        # List current restrictions
        if options["list"]:
            restrictions = TokenIPRestriction.objects.filter(token=token)
            if restrictions.exists():
                self.stdout.write(self.style.SUCCESS("Current IP restrictions:"))
                for r in restrictions:
                    self.stdout.write(f"- {r.ip_range}")
            else:
                self.stdout.write(
                    self.style.WARNING("No IP restrictions (open access)")
                )
            return

        # Reset to default open policy
        if options["reset"]:
            if not options["force"]:
                confirm = input(
                    "This will remove all IP restrictions and "
                    "allow access from any IP. Continue? [y/N] "
                )
                if confirm.lower() != "y":
                    self.stdout.write(self.style.WARNING("Operation cancelled"))
                    return

            # Delete all existing restrictions
            TokenIPRestriction.objects.filter(token=token).delete()

            # Create new restrictions
            TokenIPRestriction.objects.create(token=token, ip_range="0.0.0.0/0")
            TokenIPRestriction.objects.create(token=token, ip_range="::/0")

            self.stdout.write(self.style.SUCCESS("Token reset to default open policy"))
            return

        # Add IP restriction
        if options["add"]:
            cidr = options["add"]

            if not TokenIPRestriction.validate_cidr(cidr):
                raise CommandError(f"Invalid CIDR notation: {cidr}")

            # Check if already exists
            if TokenIPRestriction.objects.filter(token=token, ip_range=cidr).exists():
                self.stdout.write(
                    self.style.WARNING(
                        f"IP restriction {cidr} already exists for this token"
                    )
                )
                return

            # If addition conflicts with open policy open policy (0.0.0.0/0)
            # or open IPv6 policy (::0/0), warn the user and confirm
            open_ipv4 = TokenIPRestriction.objects.filter(
                token=token, ip_range="0.0.0.0/0"
            ).exists()
            open_ipv6 = TokenIPRestriction.objects.filter(
                token=token, ip_range="::/0"
            ).exists()

            if open_ipv4 or open_ipv6:
                should_remove = False

                if options["force"]:
                    # Auto remove open policies with --force
                    should_remove = True
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            "This token currently has open access. "
                            "This action will remove the open policy."
                        )
                    )
                    confirm = input("Do you want to remove the open policy? [y/N] ")
                    if confirm.lower() == "y":
                        should_remove = True

                if should_remove:
                    if open_ipv4:
                        TokenIPRestriction.objects.filter(
                            token=token, ip_range="0.0.0.0/0"
                        ).delete()
                    if open_ipv6:
                        TokenIPRestriction.objects.filter(
                            token=token, ip_range="::/0"
                        ).delete()
                    self.stdout.write("Open policy removed")

            # Add the new restriction
            TokenIPRestriction.objects.create(token=token, ip_range=cidr)
            self.stdout.write(self.style.SUCCESS(f"Added IP restriction: {cidr}"))
            return

        # Remove IP restriction
        if options["remove"]:
            cidr = options["remove"]

            # Check if exists
            restriction = TokenIPRestriction.objects.filter(token=token, ip_range=cidr)
            if not restriction.exists():
                self.stdout.write(
                    self.style.WARNING(
                        f"IP restriction {cidr} not found for this token"
                    )
                )
                return

            # Warn if removing the last restriction
            all_restrictions = TokenIPRestriction.objects.filter(token=token)
            if all_restrictions.count() == 1 and not options["force"]:
                confirm = input("This is the last IP restriction. Continue? [y/N] ")
                if confirm.lower() != "y":
                    self.stdout.write(self.style.WARNING("Operation cancelled"))
                    return

            restriction.delete()
            self.stdout.write(self.style.SUCCESS(f"Removed IP restriction: {cidr}"))
