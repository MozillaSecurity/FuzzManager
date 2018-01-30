from django.conf import settings  # noqa
import os
import sys

# Add the server basedir to PYTHONPATH so Celery on the command line
# can find the Django settings imports and packages properly
BASE_DIR = os.path.dirname(os.path.realpath(__file__))
sys.path += [os.path.abspath(os.path.join(BASE_DIR, ".."))]

from celeryconf import app  # noqa


@app.task
def check_revision_update(pk):
    from covmanager.models import Collection, Repository  # noqa
    collection = Collection.objects.get(pk=pk)

    # Get the SourceCodeProvider associated with this collection
    provider = collection.repository.getInstance()

    # Check if the provider knows the specified revision
    if not provider.testRevision(collection.revision):
        # If not, update the repository
        provider.update()

    # TODO: We could double-check here that the revision is now known
    # and raise an error if not. This error would have to be propagated
    # to the user and since we already saved the collection, we can't
    # reject the client anymore.

    return
