import os

from django.core.management.base import BaseCommand, CommandError

from covmanager.models import Repository


class Command(BaseCommand):
    help = "Sets up a repository for CovManager"

    def add_arguments(self, parser):
        parser.add_argument("name", help="repository identifier")
        parser.add_argument("provider", help="SourceCodeProvider subclass")
        parser.add_argument("location", help="path to the repository root")

    def handle(self, name, provider, location, **opts):
        if not name:
            raise CommandError("Error: invalid repository name")

        if Repository.objects.filter(name=name):
            raise CommandError(f"Error: repository with name '{name}' already exists!")

        if not provider:
            raise CommandError("Error: invalid provider class")

        # also accept friendly names
        provider = {"git": "GITSourceCodeProvider", "hg": "HGSourceCodeProvider"}.get(
            provider, provider
        )
        try:
            __import__(
                f"covmanager.SourceCodeProvider.{provider}",
                fromlist=[provider.encode("utf-8")],
            )
        except ImportError:
            raise CommandError(
                f"Error: '{provider}' is not a valid source code provider!"
            )

        if not location:
            raise CommandError("Error: invalid location")

        if not os.path.isdir(location):
            raise CommandError(f"Error: location not found: {location}")

        repository = Repository()
        repository.name = name
        repository.classname = provider
        repository.location = os.path.realpath(location)

        repository.save()

        print(
            "Successfully created repository '%s' with provider '%s' located at %s"
            % (name, provider, location)
        )
