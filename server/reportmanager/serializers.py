# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
from django.core.exceptions import MultipleObjectsReturned  # noqa
from django.forms import widgets  # noqa
from django.urls import reverse
from notifications.models import Notification
from rest_framework import serializers
from rest_framework.exceptions import APIException

from .models import (
    OS,
    App,
    BreakageCategory,
    Bucket,
    Bug,
    BugProvider,
    BugzillaTemplate,
    ReportEntry,
)


class InvalidArgumentException(APIException):
    status_code = 400


class BucketSerializer(serializers.ModelSerializer):
    bug = serializers.CharField(source="bug.external_id", default=None, allow_null=True)
    # write_only here means don't try to read it automatically in
    # super().to_representation()
    # size is an annotation, so must be set manually
    bug_provider = serializers.PrimaryKeyRelatedField(
        write_only=True,
        required=False,
        queryset=BugProvider.objects.all(),
        allow_null=True,
    )
    latest_report = serializers.DateTimeField(write_only=True, required=False)
    signature = serializers.CharField(
        style={"base_template": "textarea.html"}, required=False
    )
    size = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Bucket
        fields = (
            "bug",
            "bug_provider",
            "color",
            "description",
            "domain",
            "id",
            "latest_report",
            "priority",
            "signature",
            "size",
        )
        ordering = ("-id",)
        read_only_fields = ("id",)

    def to_internal_value(self, data):
        result = super().to_internal_value(data)
        if "bug" in result and result["bug"]["external_id"] is None:
            result["bug"] = None
        return result

    def to_representation(self, obj):
        serialized = super().to_representation(obj)
        serialized["size"] = obj.size
        serialized["latest_report"] = getattr(obj, "latest_report", None)
        return serialized


class BucketVueSerializer(BucketSerializer):
    bug_closed = serializers.SerializerMethodField()
    bug_hostname = serializers.SerializerMethodField()
    bug_urltemplate = serializers.SerializerMethodField()
    view_url = serializers.SerializerMethodField()

    class Meta(BucketSerializer.Meta):
        fields = (
            *BucketSerializer.Meta.fields,
            "bug_closed",
            "bug_hostname",
            "bug_urltemplate",
            "view_url",
        )
        read_only_fields = (
            *BucketSerializer.Meta.read_only_fields,
            "bug_closed",
            "bug_hostname",
            "bug_urltemplate",
            "view_url",
        )

    def get_bug_closed(self, sig):
        if sig.bug:
            return sig.bug.closed
        return None

    def get_bug_hostname(self, sig):
        if sig.bug and sig.bug.external_type:
            return sig.bug.external_type.hostname
        return None

    def get_bug_urltemplate(self, sig):
        if sig.bug and sig.bug.external_type:
            try:
                return sig.bug.external_type.url_template % sig.bug.external_id
            except Exception:
                return None
        return None

    def get_view_url(self, sig):
        return reverse("reportmanager:bucketview", kwargs={"sig_id": sig.id})


class BugProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = BugProvider
        fields = (
            "id",
            "classname",
            "hostname",
            "url_template",
        )


class BugzillaTemplateSerializer(serializers.ModelSerializer):
    mode = serializers.SerializerMethodField()

    class Meta:
        model = BugzillaTemplate
        fields = (
            "id",
            "mode",
            "name",
            "comment",
            "product",
            "component",
            "summary",
            "version",
            "description",
            "op_sys",
            "platform",
            "priority",
            "severity",
            "alias",
            "cc",
            "assigned_to",
            "qa_contact",
            "target_milestone",
            "whiteboard",
            "keywords",
            "attrs",
            "security_group",
            "security",
            "blocks",
            "dependson",
        )
        read_only_fields = ("id", "mode")

    def get_mode(self, obj):
        return obj.mode.value


class ReportEntrySerializer(serializers.ModelSerializer):
    # We need to redefine several fields explicitly because we flatten our
    # foreign keys into these fields instead of using primary keys, hyperlinks
    # or slug fields. All of the other solutions would require the client to
    # create these instances first and issue multiple requests in total.
    app_name = serializers.CharField(source="app.name")
    app_channel = serializers.CharField(source="app.channel")
    app_version = serializers.CharField(source="app.version")
    breakage_category = serializers.CharField(source="breakage_category.value")
    os = serializers.CharField(source="os.name", max_length=63)

    class Meta:
        model = ReportEntry
        fields = (
            "app_channel",
            "app_name",
            "app_version",
            "breakage_category",
            "bucket",
            "comments",
            "details",
            "id",
            "os",
            "reported_at",
            "url",
            "uuid",
        )
        ordering = ("-id",)
        read_only_fields = ("bucket", "id")

    def create(self, attrs):
        """Create a ReportEntry instance based on the given dictionary of values
        received. We need to unflatten foreign relationships like breakage_category, os
        and app, and create the foreign objects on the fly if they don't exist in our
        database yet.
        """
        attrs["app"] = App.objects.get_or_create(
            name=attrs["app_name"],
            channel=attrs.get("app_channel"),
            version=attrs["app_version"],
        )[0]
        attrs["breakage_category"] = BreakageCategory.objects.get_or_create(
            value=attrs["breakage_category"]
        )[0]
        attrs["os"] = OS.objects.get_or_create(name=attrs["os"])[0]

        # Create our ReportEntry instance
        return super().create(attrs)


class ReportEntryVueSerializer(ReportEntrySerializer):
    view_url = serializers.SerializerMethodField()
    sig_view_url = serializers.SerializerMethodField()
    sig_new_url = serializers.SerializerMethodField()
    find_sigs_url = serializers.SerializerMethodField()

    class Meta(ReportEntrySerializer.Meta):
        fields = (
            *ReportEntrySerializer.Meta.fields,
            "view_url",
            "sig_view_url",
            "sig_new_url",
            "find_sigs_url",
        )
        read_only_fields = (
            *ReportEntrySerializer.Meta.read_only_fields,
            "view_url",
            "sig_view_url",
            "sig_new_url",
            "find_sigs_url",
        )

    def get_view_url(self, entry):
        return reverse("reportmanager:reportview", kwargs={"report_id": entry.id})

    def get_sig_view_url(self, entry):
        if entry.bucket:
            return reverse(
                "reportmanager:bucketview", kwargs={"sig_id": entry.bucket.id}
            )
        return None

    def get_sig_new_url(self, entry):
        return f"{reverse('reportmanager:bucketnew')}?report_id={entry.id}"

    def get_find_sigs_url(self, entry):
        return reverse("reportmanager:findbuckets", kwargs={"report_id": entry.id})


class NotificationSerializer(serializers.ModelSerializer):
    actor_url = serializers.SerializerMethodField()
    target_url = serializers.SerializerMethodField()
    external_bug_url = serializers.SerializerMethodField()
    data = serializers.JSONField()

    class Meta:
        model = Notification
        fields = (
            "id",
            "timestamp",
            "data",
            "description",
            "verb",
            "actor_url",
            "target_url",
            "external_bug_url",
        )

    def get_actor_url(self, notification):
        if isinstance(notification.actor, Bucket):
            return reverse(
                "reportmanager:bucketview", kwargs={"sig_id": notification.actor.id}
            )
        return None

    def get_target_url(self, notification):
        if isinstance(notification.target, ReportEntry):
            return reverse(
                "reportmanager:reportview", kwargs={"report_id": notification.target.id}
            )
        return None

    def get_external_bug_url(self, notification):
        if isinstance(notification.target, Bug):
            return (
                f"https://{notification.target.external_type.hostname}"
                f"/{notification.target.external_id}"
            )
        return None
