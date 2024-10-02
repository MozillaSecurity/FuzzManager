# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
import json
from collections import OrderedDict
from datetime import datetime, timedelta
from logging import getLogger
from uuid import uuid4

import redis
from dateutil.relativedelta import relativedelta
from django.conf import settings as django_settings
from django.core.exceptions import FieldError, PermissionDenied, SuspiciousOperation
from django.db.models import F, Q
from django.db.models.aggregates import Count, Max
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.generic import TemplateView
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic.list import ListView
from notifications.models import Notification
from rest_framework import mixins, status, viewsets
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.decorators import action
from rest_framework.exceptions import MethodNotAllowed, ValidationError
from rest_framework.filters import BaseFilterBackend, OrderingFilter
from rest_framework.response import Response

from webcompat.models import Report

from .cron import triage_new_reports
from .forms import (
    BugzillaTemplateBugForm,
    BugzillaTemplateCommentForm,
    UserSettingsForm,
)
from .models import (
    Bucket,
    BucketHit,
    BucketWatch,
    Bug,
    BugProvider,
    BugzillaTemplate,
    BugzillaTemplateMode,
    ReportEntry,
    ReportHit,
    User,
)
from .serializers import (
    BucketSerializer,
    BucketVueSerializer,
    BugProviderSerializer,
    BugzillaTemplateSerializer,
    InvalidArgumentException,
    NotificationSerializer,
    ReportEntrySerializer,
    ReportEntryVueSerializer,
)
from .tasks import bulk_delete_reports

LOG = getLogger("reportmanager.views")


class JSONDateEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat().replace("+00:00", "Z")
        return super().default(o)


def bucket_watch_create(request):
    if request.method == "POST":
        user = User.objects.get_or_create(user=request.user)[0]
        bucket = get_object_or_404(Bucket, pk=int(request.POST["bucket"]))
        for watch in BucketWatch.objects.filter(user=user, bucket=bucket):
            watch.last_report = int(request.POST["report"])
            watch.save()
            break
        else:
            BucketWatch.objects.create(
                user=user, bucket=bucket, last_report=int(request.POST["report"])
            )
        return redirect("reportmanager:bucketwatch")
    raise SuspiciousOperation()


def bucket_watch_delete(request, sigid):
    user = User.objects.get_or_create(user=request.user)[0]

    if request.method == "POST":
        entry = get_object_or_404(BucketWatch, user=user, bucket=sigid)
        entry.delete()
        return redirect("reportmanager:bucketwatch")
    if request.method == "GET":
        entry = get_object_or_404(Bucket, user=user, pk=sigid)
        return render(request, "buckets/watch_remove.html", {"entry": entry})
    raise SuspiciousOperation()


def bucket_watch_list(request):
    # for this user, list watches
    # buckets   sig       new reports   remove
    # ========================================
    # 1         crash       10          tr
    # 2         assert      0           tr
    # 3         blah        0           tr
    user = User.objects.get_or_create(user=request.user)[0]

    filters = {
        "user": user,
        "reportentry__gt": F("bucketwatch__last_report"),
    }
    # the join of Bucket+ReportEntry is a big one, and each filter() call on a related
    # field adds a join therefore this needs to be a single filter() call, otherwise we
    # get duplicate reportentries in the result.
    buckets = Bucket.objects.filter(**filters)
    buckets = buckets.annotate(new_reports=Count("reportentry"))
    # what's left is only watched buckets with new reports. we need to include other
    # watched buckets too .. which means evaluating the buckets query now
    new_buckets = list(buckets)
    # get all buckets watched by this user
    # this is the result, but we will replace any buckets also found in newBuckets
    buckets_all = Bucket.objects.filter(user=user).order_by("-id")
    buckets_all = buckets_all.annotate(last_report=F("bucketwatch__last_report"))
    buckets = list(buckets_all)
    for idx, bucket in enumerate(buckets):
        for new_idx, new_bucket in enumerate(new_buckets):
            if new_bucket == bucket:
                # replace with this one
                new_bucket.last_report = bucket.last_report
                buckets[idx] = new_bucket
                new_buckets.pop(new_idx)
                break
        else:
            bucket.new_reports = 0
    return render(request, "buckets/watch.html", {"siglist": buckets})


def bucket_watch_reports(request, sigid):
    user = User.objects.get_or_create(user=request.user)[0]
    bucket = get_object_or_404(Bucket, pk=sigid)
    watch = get_object_or_404(BucketWatch, user=user, bucket=bucket)
    return render(
        request,
        "reports/index.html",
        {"watch_id": watch.id},
    )


def bug_provider_create(request):
    if request.method == "POST":
        provider = BugProvider(
            classname=request.POST["classname"],
            hostname=request.POST["hostname"],
            url_template=request.POST["url_template"],
        )

        try:
            provider.get_instance()
        except Exception as e:
            return render(
                request,
                "providers/edit.html",
                {"provider": provider, "error_message": e},
            )

        provider.save()
        return redirect("reportmanager:bugproviders")
    elif request.method == "GET":
        return render(request, "providers/edit.html", {})
    else:
        raise SuspiciousOperation


def bug_provider_delete(request, provider_id):
    provider = get_object_or_404(BugProvider, pk=provider_id)
    if request.method == "POST":
        # Deassociate all bugs
        bugs = Bug.objects.filter(external_type=provider.pk)
        buckets = Bucket.objects.filter(bug__in=bugs)
        for bucket in buckets:
            bucket.bug = None
            bucket.save(update_fields=["bug"])

        provider.delete()
        return redirect("reportmanager:bugproviders")
    elif request.method == "GET":
        return render(request, "providers/delete.html", {"provider": provider})
    else:
        raise SuspiciousOperation


def bug_provider_edit(request, provider_id):
    provider = get_object_or_404(BugProvider, pk=provider_id)
    if request.method == "POST":
        provider.classname = request.POST["classname"]
        provider.hostname = request.POST["hostname"]
        provider.url_template = request.POST["url_template"]

        try:
            provider.get_instance()
        except Exception as e:
            return render(
                request,
                "providers/edit.html",
                {"provider": provider, "error_message": e},
            )

        provider.save()
        return redirect("reportmanager:bugproviders")
    elif request.method == "GET":
        return render(request, "providers/edit.html", {"provider": provider})
    else:
        raise SuspiciousOperation


def bug_provider_list(request):
    providers = BugProvider.objects.annotate(size=Count("bug"))
    return render(request, "providers/index.html", {"providers": providers})


def bug_provider_view(request, provider_id):
    provider = BugProvider.objects.filter(pk=provider_id).annotate(size=Count("bug"))

    if not provider:
        raise Http404

    provider = provider[0]

    return render(request, "providers/view.html", {"provider": provider})


def bugzilla_template_duplicate(request, template_id):
    clone = get_object_or_404(BugzillaTemplate, pk=template_id)
    clone.pk = None  # to autogen a new pk on save()
    clone.name = "Clone of " + clone.name
    clone.save()
    return redirect("reportmanager:templates")


def external_bug_create(request, report_id):
    entry = get_object_or_404(ReportEntry, pk=report_id)

    if not entry.bucket:
        return render_error(
            request,
            (
                "Cannot create an external bug for an issue that is not associated "
                "to a bucket/signature"
            ),
        )

    if request.method == "GET":
        if "provider" in request.GET:
            provider = get_object_or_404(BugProvider, pk=request.GET["provider"])
        else:
            user = User.objects.get_or_create(user=request.user)[0]
            provider = get_object_or_404(BugProvider, pk=user.default_provider_id)

        template = provider.get_instance().get_template_for_user(request, entry)
        data = {
            "provider": provider,
            "template": template["pk"] if template else -1,
            "entry": entry,
        }
        return render(request, "bugzilla/create_external_bug.html", data)
    raise SuspiciousOperation


def external_bug_create_comment(request, report_id):
    entry = get_object_or_404(ReportEntry, pk=report_id)

    if request.method == "GET":
        if "provider" in request.GET:
            provider = get_object_or_404(BugProvider, pk=request.GET["provider"])
        else:
            user = User.objects.get_or_create(user=request.user)[0]
            provider = get_object_or_404(BugProvider, pk=user.default_provider_id)

        template = provider.get_instance().get_template_for_user(request, entry)
        data = {
            "provider": provider,
            "template": template["pk"] if template else -1,
            "entry": entry,
        }
        return render(request, "bugzilla/create_external_comment.html", data)
    else:
        raise SuspiciousOperation


def index(request):
    return redirect("reportmanager:buckets")


def report_delete(request, report_id):
    entry = get_object_or_404(ReportEntry, pk=report_id)

    if request.method == "POST":
        entry.delete()
        return redirect("reportmanager:reports")
    elif request.method == "GET":
        return render(request, "reports/delete.html", {"entry": entry})
    else:
        raise SuspiciousOperation


def report_edit(request, report_id):
    entry = get_object_or_404(ReportEntry, pk=report_id)

    if request.method == "POST":
        # Regenerate report information and fields depending on it
        entry.reparse_report()

        return redirect("reportmanager:reportview", report_id=entry.pk)
    else:
        return render(request, "reports/edit.html", {"entry": entry})


def render_error(request, err):
    return render(request, "error.html", {"error_message": err})


def report_list(request):
    return render(request, "reports/index.html")


def report_view(request, report_id):
    entry = get_object_or_404(ReportEntry, pk=report_id)

    providers = BugProviderSerializer(BugProvider.objects.all(), many=True).data

    return render(
        request,
        "reports/view.html",
        {"entry": entry, "providers": json.dumps(providers)},
    )


def settings(request):
    return render(request, "settings.html")


def signature_create(request):
    if request.method != "GET":
        raise SuspiciousOperation

    data = {}
    if "report_id" in request.GET:
        report_entry = get_object_or_404(ReportEntry, pk=request.GET["report_id"])

        report_info = Report.from_raw_report_data(
            report_entry.raw_stdout,
            report_entry.raw_stderr,
            report_entry.raw_report_data,
        )

        error_msg = None

        # First try to create the signature with the report address included.
        # However, if that fails, try without forcing the report signature.
        proposed_signature = report_info.create_report_signature()

        proposed_signature = str(proposed_signature)
        proposed_short_desc = report_info.create_short_signature()

        data = {
            "proposed_sig": json.loads(proposed_signature),
            "proposed_desc": proposed_short_desc,
            "warning_message": error_msg,
        }

    return render(request, "buckets/edit.html", data)


def signature_delete(request, sig_id):
    bucket = Bucket.objects.get(pk=sig_id)

    if request.method == "POST":
        if "delentries" not in request.POST:
            # Make sure we remove this bucket from all report entries referring to it,
            # otherwise these would be deleted as well through cascading.
            ReportEntry.objects.filter(bucket=bucket).update(bucket=None)
            triage_new_reports.delay()

        bucket.delete()
        return redirect("reportmanager:buckets")

    elif request.method == "GET":
        return render(
            request,
            "buckets/delete.html",
            {
                "bucket": bucket,
                "affected": ReportEntry.objects.filter(bucket=bucket).count(),
            },
        )
    else:
        raise SuspiciousOperation


def signature_edit(request, sig_id):
    if request.method != "GET" or sig_id is None:
        raise SuspiciousOperation

    bucket = get_object_or_404(Bucket, pk=sig_id)

    proposed_signature = None
    if "fit" in request.GET:
        entry = get_object_or_404(ReportEntry, pk=request.GET["fit"])
        proposed_signature = bucket.get_signature().fit(entry.get_report())

    return render(
        request,
        "buckets/edit.html",
        {"bucket": bucket, "proposed_sig": proposed_signature},
    )


def signature_find(request, report_id):
    entry = get_object_or_404(ReportEntry, pk=report_id)

    entry.reportinfo = entry.get_report()

    buckets = Bucket.objects.all()
    similar_buckets = []
    matching_bucket = None

    # Avoid hitting the database multiple times when looking for the first
    # entry of a bucket. Keeping these in memory is less expensive.
    first_entry_per_bucket_cache = {}

    for bucket in buckets:
        signature = bucket.get_signature()
        distance = signature.get_distance(entry.reportinfo)

        # We found a matching bucket, no need to display/calculate similar buckets
        if distance == 0:
            matching_bucket = bucket
            break

        # TODO: This could be made configurable through a GET parameter
        if distance <= 4:
            proposed_report_signature = signature.fit(entry.reportinfo)
            if proposed_report_signature:
                # We now try to determine how this signature will behave in other
                # buckets. If the signature matches lots of other buckets as well, it is
                # likely too broad and we should not consider it (or later rate it worse
                # than others).
                matches_in_other_buckets = 0
                matches_in_other_buckets_limit_exceeded = False
                non_matches_in_other_buckets = 0
                other_matching_bucket_ids = []
                for other_bucket in buckets:
                    if other_bucket.pk == bucket.pk:
                        continue

                    if other_bucket.pk not in first_entry_per_bucket_cache:
                        c = ReportEntry.objects.filter(bucket=other_bucket).first()
                        first_entry_per_bucket_cache[other_bucket.pk] = c
                        if c:
                            first_entry_per_bucket_cache[other_bucket.pk] = (
                                c.get_report()
                            )

                    first_entry_report_info = first_entry_per_bucket_cache[
                        other_bucket.pk
                    ]
                    if first_entry_report_info:
                        if proposed_report_signature.matches(first_entry_report_info):
                            matches_in_other_buckets += 1
                            other_matching_bucket_ids.append(other_bucket.pk)

                            # We already match too many foreign buckets. Abort our
                            # search here to speed up the response time.
                            if matches_in_other_buckets > 5:
                                matches_in_other_buckets_limit_exceeded = True
                                break
                        else:
                            non_matches_in_other_buckets += 1

                bucket.off_count = distance

                if matches_in_other_buckets + non_matches_in_other_buckets > 0:
                    bucket.foreign_match_percentage = round(
                        (
                            float(matches_in_other_buckets)
                            / (matches_in_other_buckets + non_matches_in_other_buckets)
                        )
                        * 100,
                        2,
                    )
                else:
                    bucket.foreign_match_percentage = 0

                bucket.foreign_match_count = matches_in_other_buckets
                bucket.foreign_match_limit_exceeded = (
                    matches_in_other_buckets_limit_exceeded
                )

                if matches_in_other_buckets == 0:
                    bucket.foreign_color = "green"
                elif matches_in_other_buckets < 3:
                    bucket.foreign_color = "yellow"
                else:
                    bucket.foreign_color = "red"

                # Only include the bucket in our results if the number of matches in
                # other buckets is below out limit. Otherwise, it will just distract
                # the user.
                if matches_in_other_buckets <= 5:
                    bucket.link_to_others = ",".join(
                        [str(x) for x in other_matching_bucket_ids]
                    )
                    similar_buckets.append(bucket)

    if matching_bucket:
        entry.bucket = matching_bucket
        entry.save(update_fields=["bucket"])
        return render(
            request,
            "buckets/find.html",
            {"bucket": matching_bucket, "reportentry": entry},
        )
    else:
        similar_buckets.sort(key=lambda x: (x.foreign_match_count, x.off_count))
        return render(
            request,
            "buckets/find.html",
            {"buckets": similar_buckets, "reportentry": entry},
        )


def signature_list(request):
    providers = BugProviderSerializer(BugProvider.objects.all(), many=True).data
    return render(
        request,
        "buckets/index.html",
        {
            "providers": json.dumps(providers),
            "activity_range": getattr(
                django_settings, "CLEANUP_REPORTS_AFTER_DAYS", 14
            ),
        },
    )


def signature_optimize(request, sig_id):
    bucket = get_object_or_404(Bucket, pk=sig_id)

    # Get all unbucketed entries
    entries = (
        ReportEntry.objects.filter(bucket=None)
        .order_by("-id")
        .select_related("app", "breakage_category", "os")
    )

    (optimized_signature, matching_entries) = bucket.optimize_signature(entries)
    diff = None
    if optimized_signature:
        diff = bucket.get_signature().get_signature_unified_diff_tuples(
            matching_entries[0].reportinfo
        )

    return render(
        request,
        "buckets/optimize.html",
        {
            "bucket": bucket,
            "optimized_signature": optimized_signature,
            "diff": diff,
            "matching_entries": matching_entries,
        },
    )


def signature_try(request, sig_id, report_id):
    bucket = get_object_or_404(Bucket, pk=sig_id)

    entry = get_object_or_404(ReportEntry, pk=report_id)

    signature = bucket.get_signature()
    entry.reportinfo = entry.get_report()

    # symptoms = signature.get_symptoms_diff(entry.reportinfo)
    diff = signature.get_signature_unified_diff_tuples(entry.reportinfo)

    return render(
        request, "buckets/try.html", {"bucket": bucket, "entry": entry, "diff": diff}
    )


def signature_view(request, sig_id):
    response = BucketVueViewSet.as_view({"get": "retrieve"})(request, pk=sig_id)
    if response.status_code == 404:
        raise Http404
    elif response.status_code != 200:
        return response
    bucket = response.data
    providers = BugProviderSerializer(BugProvider.objects.all(), many=True).data

    return render(
        request,
        "buckets/view.html",
        {
            "activity_range": getattr(
                django_settings, "CLEANUP_REPORTS_AFTER_DAYS", 14
            ),
            "bucket": json.dumps(bucket, cls=JSONDateEncoder),
            "bucket_id": bucket["id"],
            "providers": json.dumps(providers),
            "description": bucket["description"],
        },
    )


def stats(request):
    providers = BugProviderSerializer(BugProvider.objects.all(), many=True).data

    return render(
        request,
        "stats.html",
        {
            "activity_range": getattr(
                django_settings, "CLEANUP_REPORTS_AFTER_DAYS", 30
            ),
            "providers": json.dumps(providers or []),
        },
    )


class JsonQueryFilterBackend(BaseFilterBackend):
    """
    Accepts filtering with a query parameter which builds a Django query from JSON
    (see json_to_query)
    """

    def filter_queryset(self, request, queryset, view):
        """
        Return a filtered queryset.
        """
        querystr = request.query_params.get("query", None)
        if querystr is not None:
            try:
                _, queryobj = json_to_query(querystr)
            except (RuntimeError, TypeError) as e:
                raise InvalidArgumentException(f"error in query: {e}")
            try:
                queryset = queryset.filter(queryobj)
            except FieldError as exc:
                raise InvalidArgumentException(f"error in query: {exc}")
        return queryset


class BucketAnnotateFilterBackend(BaseFilterBackend):
    """Annotates bucket queryset with size"""

    def filter_queryset(self, request, queryset, view):
        return queryset.annotate(
            size=Count("reportentry"),
            latest_report=Max("reportentry__reported_at"),
            latest_entry_id=Max("reportentry__id"),
        )


class WatchFilterReportsBackend(BaseFilterBackend):
    """Filters the queryset to retrieve watched entries if '?watch=<int>'"""

    def filter_queryset(self, request, queryset, view):
        watch_id = request.query_params.get("watch", "false").lower()
        if watch_id == "false":
            return queryset
        watch = BucketWatch.objects.get(id=watch_id)
        return queryset.filter(bucket=watch.bucket, id__gt=watch.last_report)


class AsyncOpViewSet(viewsets.GenericViewSet):
    """API endpoint for polling async operations"""

    authentication_classes = (TokenAuthentication, SessionAuthentication)
    lookup_value_regex = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"

    def retrieve(self, request, pk=None):
        assert isinstance(pk, str)
        cache = redis.StrictRedis.from_url(django_settings.REDIS_URL)
        if cache.sismember("cm_async_operations", pk):
            return Response(status=status.HTTP_202_ACCEPTED)
        return Response(status=status.HTTP_200_OK)


class ReportEntryViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """API endpoint that allows adding/viewing ReportEntries"""

    authentication_classes = (TokenAuthentication, SessionAuthentication)
    queryset = ReportEntry.objects.all().select_related(
        "app",
        "breakage_category",
        "os",
    )
    serializer_class = ReportEntrySerializer
    filter_backends = (
        JsonQueryFilterBackend,
        OrderingFilter,
        WatchFilterReportsBackend,
    )

    def get_serializer(self, *args, **kwds):
        self.vue = self.request.query_params.get("vue", "false").lower() not in (
            "false",
            "0",
        )
        if self.vue:
            return ReportEntryVueSerializer(*args, **kwds)
        else:
            return super().get_serializer(*args, **kwds)

    @action(detail=False, methods=["delete"])
    def delete(self, request, pk=None):
        if pk is not None:
            raise MethodNotAllowed(request.method)
        queryset = self.filter_queryset(self.get_queryset())
        token = f"{uuid4()}"
        cache = redis.StrictRedis.from_url(django_settings.REDIS_URL)
        cache.sadd("cm_async_operations", token)
        bulk_delete_reports.delay(queryset.query, token)
        return Response(
            status=status.HTTP_202_ACCEPTED,
            data=token,
        )

    def partial_update(self, request, pk=None):
        """Update individual report fields."""
        allowed_fields = {}
        try:
            obj = ReportEntry.objects.get(pk=pk)
        except ReportEntry.DoesNotExist as exc:
            raise Http404 from exc
        given_fields = set(request.data.keys())
        disallowed_fields = given_fields - allowed_fields
        if disallowed_fields:
            if len(disallowed_fields) == 1:
                error_str = f"field {disallowed_fields.pop()!r}"
            else:
                error_str = f"fields {list(disallowed_fields)!r}"
            raise InvalidArgumentException(f"{error_str} cannot be updated")
        return Response(ReportEntrySerializer(obj).data)


class BucketViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """API endpoint that allows viewing Buckets"""

    authentication_classes = (TokenAuthentication, SessionAuthentication)
    queryset = Bucket.objects.all().select_related("bug", "bug__external_type")
    serializer_class = BucketSerializer
    filter_backends = (
        BucketAnnotateFilterBackend,
        JsonQueryFilterBackend,
        OrderingFilter,
    )
    ordering_fields = (
        "id",
        "description",
        "size",
        "priority",
        "bug__external_id",
    )

    def get_serializer(self, *args, **kwds):
        self.vue = self.request.query_params.get("vue", "false").lower() not in (
            "false",
            "0",
        )
        if self.vue:
            return BucketVueSerializer(*args, **kwds)
        else:
            return super().get_serializer(*args, **kwds)

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)

        if self.vue and response.status_code == 200:
            hits = (
                BucketHit.objects.all()
                .filter(
                    begin__gte=timezone.now()
                    - timedelta(
                        days=getattr(django_settings, "CLEANUP_REPORTS_AFTER_DAYS", 14)
                    ),
                    bucket_id__in=[bucket["id"] for bucket in response.data["results"]],
                )
                .order_by("begin")
            )

            bucket_hits = {}
            for bucket, begin, num in hits.values_list("bucket_id", "begin", "count"):
                bucket_hits.setdefault(bucket, {})
                bucket_hits[bucket].setdefault(begin, 0)
                bucket_hits[bucket][begin] += num

            for bucket in response.data["results"]:
                bucket["report_history"] = [
                    {"begin": begin, "count": num}
                    for begin, num in bucket_hits.get(bucket["id"], {}).items()
                ]

        return response

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        serializer = self.get_serializer(instance)
        response = Response(serializer.data)

        if self.vue and response.status_code == 200:
            hits = (
                BucketHit.objects.all()
                .filter(
                    begin__gte=timezone.now()
                    - timedelta(
                        days=getattr(django_settings, "CLEANUP_REPORTS_AFTER_DAYS", 14)
                    ),
                    bucket_id=response.data["id"],
                )
                .order_by("begin")
            )

            response.data["report_history"] = list(hits.values("begin", "count"))

        return response

    def __validate(self, bucket, submit_save, reassign, limit, offset, created):
        try:
            bucket.get_signature()
        except RuntimeError as e:
            raise ValidationError(f"Signature is not valid: {e}")

        # Only save if we hit "save" (not e.g. "preview")
        # If offset is set, don't do it again (already done on first iteration)
        if submit_save and not offset:
            if bucket.bug is not None:
                bucket.bug.save()
                # this is not a no-op!
                # if the bug was just created by .save(),
                # it must be re-assigned to the model
                # ref: https://docs.djangoproject.com/en/3.1/topics/db
                #      /examples/many_to_one/
                # "Note that you must save an object before it can be
                #  assigned to a foreign key relationship."
                bucket.bug = bucket.bug
            if reassign:
                bucket.reassign_in_progress = True
            bucket.save()
            result = status.HTTP_201_CREATED
        else:
            result = status.HTTP_200_OK

        # there are 4 cases:
        # reassign & save: expensive and slow
        # ressign & preview: do a limited reassignment and return results for preview
        # no-reassign & preview: same as above, but change results are empty
        # no-reassign & save: save bucket without reprocessing, s.b. instant

        in_list, out_list = [], []
        in_list_count, out_list_count = 0, 0
        next_offset = None
        # If the reassign checkbox is checked
        if reassign:
            (
                in_list,
                out_list,
                in_list_count,
                out_list_count,
                next_offset,
            ) = bucket.reassign(submit_save, limit=limit, offset=offset)
            if submit_save and not next_offset:
                Bucket.objects.filter(pk=bucket.pk).update(reassign_in_progress=False)

        data = {
            "in_list": in_list,
            "out_list": out_list,
            "in_list_count": in_list_count,
            "out_list_count": out_list_count,
            "next_offset": next_offset,
        }

        # Save bucket and redirect to viewing it
        if submit_save:
            if next_offset is None:
                data["url"] = reverse(
                    "reportmanager:bucketview", kwargs={"sig_id": bucket.pk}
                )
        else:
            data["warning_message"] = "This is a preview, don't forget to save!"

        return Response(
            status=result,
            data=data,
        )

    def update(self, request, *args, **kwargs):
        raise MethodNotAllowed(request.method)

    def partial_update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        bucket = get_object_or_404(Bucket, id=self.kwargs["pk"])

        if "bug" in serializer.validated_data:
            if serializer.validated_data["bug"] is None:
                bug = None
            else:
                bug = Bug.objects.filter(
                    external_id=serializer.validated_data.get("bug")["external_id"],
                    external_type=serializer.validated_data.get("bug_provider"),
                )
                if not bug.exists():
                    bug = Bug(
                        external_id=serializer.validated_data.get("bug")["external_id"],
                        external_type=serializer.validated_data.get("bug_provider"),
                    )
                else:
                    bug = bug.first()

            bucket.bug = bug

        if "hide_until" in serializer.validated_data:
            bucket.hide_until = serializer.validated_data["hide_until"]
        if "signature" in serializer.validated_data:
            bucket.signature = serializer.validated_data["signature"]
        if "priority" in serializer.validated_data:
            bucket.priority = serializer.validated_data["priority"]
        if "description" in serializer.validated_data:
            bucket.description = serializer.validated_data["description"]

        save = request.query_params.get("save", "true").lower() not in ("false", "0")
        reassign = request.query_params.get("reassign", "true").lower() not in (
            "false",
            "0",
        )
        if reassign:
            limit = int(request.query_params.get("limit", "1000"))
            offset = int(request.query_params.get("offset", "0"))
        else:
            limit = offset = None
        return self.__validate(bucket, save, reassign, limit, offset, created=False)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        bucket = Bucket(
            signature=serializer.validated_data.get("signature"),
            priority=serializer.validated_data.get("priority"),
            description=serializer.validated_data.get("description"),
        )

        save = request.query_params.get("save", "true").lower() not in ("false", "0")
        reassign = request.query_params.get("reassign", "true").lower() not in (
            "false",
            "0",
        )
        if reassign:
            limit = int(request.query_params.get("limit", "1000"))
            offset = int(request.query_params.get("offset", "0"))
        else:
            limit = offset = None
        return self.__validate(bucket, save, reassign, limit, offset, created=save)


class BucketVueViewSet(BucketViewSet):
    """API endpoint that allows viewing Buckets and always uses Vue serializer"""

    def get_serializer(self, *args, **kwds):
        self.vue = True
        return BucketVueSerializer(*args, **kwds)


class BugProviderViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    API endpoint that allows listing BugProviders
    """

    authentication_classes = (TokenAuthentication, SessionAuthentication)
    queryset = BugProvider.objects.all()
    serializer_class = BugProviderSerializer


class BugzillaTemplateViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """
    API endpoint that allows viewing BugzillaTemplates
    """

    authentication_classes = (TokenAuthentication, SessionAuthentication)
    queryset = BugzillaTemplate.objects.all()
    serializer_class = BugzillaTemplateSerializer


class NotificationViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    API endpoint that allows listing unread Notifications
    """

    authentication_classes = (TokenAuthentication, SessionAuthentication)
    serializer_class = NotificationSerializer
    filter_backends = (JsonQueryFilterBackend,)

    def get_queryset(self):
        return Notification.objects.unread().filter(recipient=self.request.user)

    @action(detail=True, methods=["patch"])
    def mark_as_read(self, request, pk=None):
        notification = self.get_object()

        if notification.recipient != request.user:
            raise PermissionDenied()

        notification.mark_as_read()
        return Response(status=status.HTTP_200_OK)

    @action(detail=False, methods=["patch"])
    def mark_all_as_read(self, request):
        notifications = self.get_queryset()
        notifications.mark_all_as_read()
        return Response(status=status.HTTP_200_OK)


def json_to_query(json_str):
    """
    This method converts JSON objects into trees of Django Q objects.
    It can be used to provide the user the ability to perform complex
    queries on the database using JSON as a query string.

    The decoded JSON may only contain objects. Each object must contain
    an "op" key that describes the operation of the object. This can either
    be "AND", "OR" or "NOT". Right now, it is mandatory to specify an operator
    even if there is only one element in the object.

    Any other keys in the object are interpreted as follows:

    If the value of the key is an object itself, recursively create a new
    query object and connect all query objects in the current object together
    using the specified operator. In this case, the key itself remains unused.

    If the value of the key is a string, directly interpret key and value as
    a query string for the database.

    If the operator is "NOT", then only one other key can be present in the
    object. If the operator is "AND" or "OR" and only one other key is present,
    then the operator has no effect.
    """
    try:
        obj = json.loads(json_str, object_pairs_hook=OrderedDict)
    except ValueError as e:
        raise RuntimeError(f"Invalid JSON: {e}")

    def get_query_obj(obj, key=None):
        if obj is None or isinstance(obj, (str, list, int)):
            kwargs = {key: obj}
            qobj = Q(**kwargs)
            return qobj
        elif not isinstance(obj, dict):
            raise RuntimeError(
                f"Invalid object type '{type(obj).__name__}' in query object"
            )

        qobj = Q()

        if "op" not in obj:
            raise RuntimeError("No operator specified in query object")

        op = obj["op"]
        objkeys = [value for value in obj if value != "op"]

        if op == "NOT" and len(objkeys) > 1:
            raise RuntimeError("Attempted to negate multiple objects at once")

        for objkey in objkeys:
            if op == "AND":
                qobj.add(get_query_obj(obj[objkey], objkey), Q.AND)
            elif op == "OR":
                qobj.add(get_query_obj(obj[objkey], objkey), Q.OR)
            elif op == "NOT":
                qobj = get_query_obj(obj[objkey], objkey)
                qobj.negate()
            else:
                raise RuntimeError(f"Invalid operator '{op}' specified in query object")

        return qobj

    return (obj, get_query_obj(obj))


class BugzillaTemplateListView(ListView):
    model = BugzillaTemplate
    template_name = "bugzilla/list.html"
    paginate_by = 100


class BugzillaTemplateDeleteView(DeleteView):
    model = BugzillaTemplate
    template_name = "bugzilla/delete.html"
    success_url = reverse_lazy("reportmanager:templates")
    pk_url_kwarg = "template_id"


class BugzillaTemplateEditView(UpdateView):
    model = BugzillaTemplate
    template_name = "bugzilla/create_edit.html"
    success_url = reverse_lazy("reportmanager:templates")
    pk_url_kwarg = "template_id"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Edit template"
        return context

    def get_form_class(self):
        if self.object.mode == BugzillaTemplateMode.Bug:
            return BugzillaTemplateBugForm
        else:
            return BugzillaTemplateCommentForm


class BugzillaTemplateBugCreateView(CreateView):
    model = BugzillaTemplate
    template_name = "bugzilla/create_edit.html"
    form_class = BugzillaTemplateBugForm
    success_url = reverse_lazy("reportmanager:templates")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Create a bug template"
        return context

    def form_valid(self, form):
        form.instance.mode = BugzillaTemplateMode.Bug
        return super().form_valid(form)


class BugzillaTemplateCommentCreateView(CreateView):
    model = BugzillaTemplate
    template_name = "bugzilla/create_edit.html"
    form_class = BugzillaTemplateCommentForm
    success_url = reverse_lazy("reportmanager:templates")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["title"] = "Create a comment template"
        return context

    def form_valid(self, form):
        form.instance.mode = BugzillaTemplateMode.Comment
        return super().form_valid(form)


class UserSettingsEditView(UpdateView):
    model = User
    template_name = "usersettings.html"
    form_class = UserSettingsForm
    success_url = reverse_lazy("reportmanager:usersettings")

    def get_form_kwargs(self, **kwargs):
        kwargs = super().get_form_kwargs(**kwargs)
        kwargs["user"] = self.get_queryset().get(user=self.request.user)
        return kwargs

    def get_object(self):
        return self.get_queryset().get(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["bugzilla_providers"] = BugProvider.objects.filter(
            classname="BugzillaProvider"
        )
        context["user"] = self.request.user
        return context


class InboxView(TemplateView):
    template_name = "inbox.html"


class _FreqCount:
    def __init__(self):
        self.hour = 0
        self.day = 0
        self.week = 0
        self.month = 0
        self.bucket_hour = {}
        self.bucket_day = {}
        self.bucket_week = {}
        self.bucket_month = {}

    def add_hour(self, bucket):
        self.hour += 1
        if bucket is not None:
            self.bucket_hour.setdefault(bucket, 0)
            self.bucket_hour[bucket] += 1
        self.add_day(bucket)

    def add_day(self, bucket):
        self.day += 1
        if bucket is not None:
            self.bucket_day.setdefault(bucket, 0)
            self.bucket_day[bucket] += 1
        self.add_week(bucket)

    def add_week(self, bucket):
        self.week += 1
        if bucket is not None:
            self.bucket_week.setdefault(bucket, 0)
            self.bucket_week[bucket] += 1
        self.add_month(bucket)

    def add_month(self, bucket):
        self.month += 1
        if bucket is not None:
            self.bucket_month.setdefault(bucket, 0)
            self.bucket_month[bucket] += 1


class ReportStatsViewSet(viewsets.GenericViewSet):
    """
    API endpoint that allows retrieving ReportManager statistics
    """

    authentication_classes = (TokenAuthentication, SessionAuthentication)
    queryset = ReportEntry.objects.all()
    filter_backends = ()

    def retrieve(self, request, *_args, **_kwds):
        LOG.error("in retrieve")
        entries = self.filter_queryset(self.get_queryset())

        now = timezone.now()
        last_day = now - timedelta(days=1)
        last_week = now - timedelta(days=7)
        last_month = now - relativedelta(months=1)
        entries = entries.filter(reported_at__gt=last_month)

        totals = _FreqCount()
        for reported_at, bucket_id in entries.values_list("reported_at", "bucket_id"):
            if reported_at > last_day:
                totals.add_day(bucket_id)
            elif reported_at > last_week:
                totals.add_week(bucket_id)
            else:
                totals.add_month(bucket_id)

        # this gives all the bucket ids
        #   where the bucket is top10 for any period (day, week, month)
        top10s = (
            {
                b_id
                for b_id, _ in sorted(
                    totals.bucket_day.items(), key=lambda t: t[1], reverse=True
                )[:10]
            }
            | {
                b_id
                for b_id, _ in sorted(
                    totals.bucket_week.items(), key=lambda t: t[1], reverse=True
                )[:10]
            }
            | {
                b_id
                for b_id, _ in sorted(
                    totals.bucket_month.items(), key=lambda t: t[1], reverse=True
                )[:10]
            }
        )

        frequent_buckets = {}
        for b_id in top10s:
            frequent_buckets[b_id] = [
                totals.bucket_day.get(b_id, 0),
                totals.bucket_week.get(b_id, 0),
                totals.bucket_month[b_id],  # only one that's guaranteed to exist
            ]

        n_periods = getattr(django_settings, "REPORT_STATS_MAX_HISTORY_DAYS", 14) * 24
        cur_period = ReportHit.get_period(now)
        periods = [cur_period - timedelta(hours=n) for n in range(n_periods)]
        periods.reverse()
        hits_per_hour = [0 for _ in periods]
        hit_idx = 0
        for hit in ReportHit.objects.filter(
            last_update__gt=periods[0] - timedelta(hours=1),
            last_update__lte=periods[-1],
        ).order_by("last_update"):
            hit_period = ReportHit.get_period(hit.last_update)
            hit_idx = periods.index(hit_period, hit_idx)
            hits_per_hour[hit_idx] += hit.count

        return Response(
            {
                # [int, int, int] (day, week, month)
                "totals": [totals.day, totals.week, totals.month],
                # { bucket_id: [day, week, month] }
                # includes the top 10 for each time-frame, which usually overlap
                "frequent_buckets": frequent_buckets,
                # [int, ...] hits per hour for last max_history_days
                "graph_data": hits_per_hour,
            },
            status=status.HTTP_200_OK,
        )
