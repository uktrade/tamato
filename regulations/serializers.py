from rest_framework import serializers

from common.serializers import (
    ValiditySerializerMixin,
    TrackedModelSerializer,
    TrackedModelSerializerMixin,
)
from regulations import models, validators


class GroupSerializer(ValiditySerializerMixin):
    class Meta:
        model = models.Group
        fields = [
            "group_id",
            "description",
        ]


class NestedRegulationSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Regulation
        fields = ["url", "regulation_id"]


@TrackedModelSerializer.register_polymorphic_model
class AmendmentSerializer(
    serializers.HyperlinkedModelSerializer, TrackedModelSerializerMixin
):
    class Meta:
        model = models.Amendment
        fields = [
            "enacting_regulation",
            "target_regulation",
            "update_type",
            "record_code",
            "subrecord_code",
            "taric_template",
        ]


class NestedAmendmentSerializer(serializers.HyperlinkedModelSerializer):
    regulation = NestedRegulationSerializer()

    class Meta:
        model = models.Amendment
        fields = ["enacting_regulation"]


@TrackedModelSerializer.register_polymorphic_model
class ReplacementSerializer(
    serializers.HyperlinkedModelSerializer, TrackedModelSerializerMixin
):
    class Meta:
        model = models.Replacement
        fields = [
            "enacting_regulation",
            "target_regulation",
            "update_type",
            "record_code",
            "subrecord_code",
            "taric_template",
        ]


class NestedReplacementSerializer(serializers.HyperlinkedModelSerializer):
    regulation = NestedRegulationSerializer()

    class Meta:
        model = models.Replacement
        fields = ["enacting_regulation"]


@TrackedModelSerializer.register_polymorphic_model
class ExtensionSerializer(
    serializers.HyperlinkedModelSerializer, TrackedModelSerializerMixin
):
    class Meta:
        model = models.Extension
        fields = [
            "enacting_regulation",
            "target_regulation",
            "effective_end_date",
            "update_type",
            "record_code",
            "subrecord_code",
            "taric_template",
        ]


class NestedExtensionSerializer(serializers.HyperlinkedModelSerializer):
    regulation = NestedRegulationSerializer()

    class Meta:
        model = models.Extension
        fields = ["enacting_regulation", "effective_end_date"]


@TrackedModelSerializer.register_polymorphic_model
class SuspensionSerializer(
    serializers.HyperlinkedModelSerializer, TrackedModelSerializerMixin
):
    class Meta:
        model = models.Suspension
        fields = [
            "enacting_regulation",
            "target_regulation",
            "effective_end_date",
            "update_type",
            "record_code",
            "subrecord_code",
            "taric_template",
        ]


class NestedSuspensionSerializer(serializers.HyperlinkedModelSerializer):
    regulation = NestedRegulationSerializer()

    class Meta:
        model = models.Suspension
        fields = ["enacting_regulation", "effective_end_date"]


@TrackedModelSerializer.register_polymorphic_model
class TerminationSerializer(
    serializers.HyperlinkedModelSerializer, TrackedModelSerializerMixin
):
    class Meta:
        model = models.Termination
        fields = [
            "enacting_regulation",
            "target_regulation",
            "effective_date",
            "update_type",
            "record_code",
            "subrecord_code",
            "taric_template",
        ]


class NestedTerminationSerializer(serializers.HyperlinkedModelSerializer):
    regulation = NestedRegulationSerializer()

    class Meta:
        model = models.Termination
        fields = ["enacting_regulation", "effective_date"]


class RoleTypeSerializer(serializers.Serializer):
    def to_representation(self, instance):
        """Convert integer to RoleType"""
        return {
            "value": instance,
            "label": dict(validators.RoleType.choices)[instance],
        }


@TrackedModelSerializer.register_polymorphic_model
class RegulationSerializer(
    serializers.HyperlinkedModelSerializer,
    ValiditySerializerMixin,
    TrackedModelSerializerMixin,
):
    regulation_group = GroupSerializer()
    role_type = RoleTypeSerializer()
    amends = NestedRegulationSerializer(many=True)
    amendments = NestedAmendmentSerializer(many=True)
    extends = NestedRegulationSerializer(many=True)
    extensions = NestedExtensionSerializer(many=True)
    suspends = NestedRegulationSerializer(many=True)
    suspensions = NestedSuspensionSerializer(many=True)
    terminates = NestedRegulationSerializer(many=True)
    terminations = NestedTerminationSerializer(many=True)
    replaces = NestedRegulationSerializer(many=True)
    replacements = NestedReplacementSerializer(many=True)

    published_date = serializers.SerializerMethodField()
    effective_end_date = serializers.SerializerMethodField()

    def get_published_date(self, obj):
        if obj.published_at:
            return self.date_format_string.format(obj.published_at)

    def get_effective_end_date(self, obj):
        if obj.effective_end_date:
            return self.date_format_string.format(obj.published_at)

    class Meta:
        model = models.Regulation
        fields = [
            "url",
            "role_type",
            "regulation_id",
            "official_journal_number",
            "official_journal_page",
            "published_date",
            "information_text",
            "approved",
            "replacement_indicator",
            "stopped",
            "effective_end_date",
            "community_code",
            "regulation_group",
            "valid_between",
            "effective_end_date",
            "amends",
            "amendments",
            "extends",
            "extensions",
            "suspends",
            "suspensions",
            "terminates",
            "terminations",
            "replaces",
            "replacements",
            "update_type",
            "record_code",
            "subrecord_code",
            "taric_template",
            "start_date",
            "end_date",
        ]
