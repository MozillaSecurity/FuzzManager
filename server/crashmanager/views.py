from rest_framework import viewsets
from crashmanager.serializers import BucketSerializer, CrashEntrySerializer
from crashmanager.models import CrashEntry, Bucket


class CrashEntryViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows adding/viewing CrashEntries
    """
    queryset = CrashEntry.objects.all()
    serializer_class = CrashEntrySerializer


class BucketViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows reading of signatures
    """
    queryset = Bucket.objects.all()
    serializer_class = BucketSerializer