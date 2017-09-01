# Ensure print() compatibility with Python 3
from __future__ import print_function

from django.core.management.base import BaseCommand, CommandError
import sys

from covmanager.models import Repository

class Command(BaseCommand):
    help = 'Sets up a repository for CovManager'

    def handle(self, *args, **opts):
        if len(args) < 3:
            print("Error: Usage is %s setup_repository <name> <provider> <location>" % sys.argv[0], file=sys.stderr)
            sys.exit(1)

        name = args[0]
        provider = args[1]
        location = args[2]

        if Repository.objects.filter(name=name):
            print("Error: Repository with name '%s' already exists!" % name, file=sys.stderr)
            sys.exit(1)

        try:
            __import__('covmanager.SourceCodeProvider.%s' % provider, fromlist=[provider])
        except ImportError:
            print("Error: Provider '%s' is not a valid source code provider!" % provider, file=sys.stderr)
            sys.exit(1)

        repository = Repository()
        repository.name = name
        repository.classname = provider
        repository.location = location

        repository.save()

        print("Successfully created repository '%s' with provider '%s' located at %s" % (name, provider, location))