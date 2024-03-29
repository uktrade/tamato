from django.core.validators import RegexValidator
from rest_framework import serializers

from common.serializers import TARIC3DateRangeField
from common.serializers import TrackedModelSerializer
from common.serializers import TrackedModelSerializerMixin
from common.serializers import ValiditySerializerMixin
from regulations import models
from regulations import validators


@TrackedModelSerializer.register_polymorphic_model
class GroupSerializer(ValiditySerializerMixin, TrackedModelSerializerMixin):
    group_id = serializers.CharField(
        max_length=3,
        validators=[RegexValidator(r"[A-Z][A-Z][A-Z]")],
    )

    class Meta:
        model = models.Group
        fields = [
            "group_id",
            "description",
            "update_type",
            "valid_between",
            "record_code",
            "subrecord_code",
            "description_subrecord_code",
            "taric_template",
            "start_date",
            "end_date",
        ]


class NestedRegulationSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = models.Regulation
        fields = ["url", "regulation_id"]


class BaseRegulationSerializer(
    ValiditySerializerMixin,
    TrackedModelSerializerMixin,
):
    role_type = serializers.IntegerField(read_only=False)
    regulation_group = GroupSerializer(required=False)
    regulation_id = serializers.CharField(
        max_length=8,
        validators=[validators.regulation_id_validator],
        read_only=False,
    )

    compound_information_text = serializers.SerializerMethodField()
    official_journal_number = serializers.CharField(read_only=False, required=False)
    official_journal_page = serializers.IntegerField(read_only=False, required=False)
    published_at = serializers.DateField(read_only=False, required=False)
    effective_end_date = serializers.DateField(read_only=False, required=False)
    replacement_indicator = serializers.IntegerField(read_only=False)
    valid_between = TARIC3DateRangeField(required=False)

    def get_compound_information_text(self, obj):
        parts = [obj.information_text, obj.public_identifier, obj.url]
        if any(parts):
            return "|".join([p or "" for p in parts])

    class Meta:
        model = models.Regulation
        fields = [
            "url",
            "role_type",
            "regulation_id",
            "regulation_group",
            "official_journal_number",
            "official_journal_page",
            "published_at",
            "compound_information_text",
            "information_text",
            "public_identifier",
            "url",
            "approved",
            "replacement_indicator",
            "stopped",
            "effective_end_date",
            "community_code",
            "valid_between",
            "effective_end_date",
            "update_type",
            "taric_template",
            "start_date",
            "end_date",
        ]


@TrackedModelSerializer.register_polymorphic_model
class AmendmentSerializer(TrackedModelSerializerMixin):
    enacting_regulation = BaseRegulationSerializer()
    target_regulation = BaseRegulationSerializer(read_only=True)

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
    enacting_regulation = NestedRegulationSerializer()

    class Meta:
        model = models.Amendment
        fields = ["enacting_regulation"]


@TrackedModelSerializer.register_polymorphic_model
class ReplacementSerializer(TrackedModelSerializerMixin):
    enacting_regulation = BaseRegulationSerializer(read_only=True)
    target_regulation = BaseRegulationSerializer(read_only=True)

    class Meta:
        model = models.Replacement
        fields = [
            "enacting_regulation",
            "target_regulation",
            "measure_type_id",
            "geographical_area_id",
            "chapter_heading",
            "update_type",
            "record_code",
            "subrecord_code",
            "taric_template",
        ]


class NestedReplacementSerializer(serializers.HyperlinkedModelSerializer):
    enacting_regulation = NestedRegulationSerializer()

    class Meta:
        model = models.Replacement
        fields = ["enacting_regulation"]


@TrackedModelSerializer.register_polymorphic_model
class ExtensionSerializer(
    serializers.HyperlinkedModelSerializer,
    TrackedModelSerializerMixin,
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
    enacting_regulation = NestedRegulationSerializer()

    class Meta:
        model = models.Extension
        fields = ["enacting_regulation", "effective_end_date"]


@TrackedModelSerializer.register_polymorphic_model
class SuspensionSerializer(TrackedModelSerializerMixin):
    enacting_regulation = BaseRegulationSerializer()
    target_regulation = BaseRegulationSerializer(read_only=True)

    class Meta:
        model = models.Suspension
        fields = [
            "enacting_regulation",
            "target_regulation",
            "effective_end_date",
            "update_type",
            "record_code",
            "subrecord_code",
            "action_record_code",
            "action_subrecord_code",
            "taric_template",
        ]


class NestedSuspensionSerializer(serializers.HyperlinkedModelSerializer):
    enacting_regulation = NestedRegulationSerializer()

    class Meta:
        model = models.Suspension
        fields = ["enacting_regulation", "effective_end_date"]


@TrackedModelSerializer.register_polymorphic_model
class TerminationSerializer(
    serializers.HyperlinkedModelSerializer,
    TrackedModelSerializerMixin,
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
    enacting_regulation = NestedRegulationSerializer()

    class Meta:
        model = models.Termination
        fields = ["enacting_regulation", "effective_date"]


@TrackedModelSerializer.register_polymorphic_model
class RegulationSerializer(
    BaseRegulationSerializer,
    ValiditySerializerMixin,
    TrackedModelSerializerMixin,
):
    regulation_group = GroupSerializer()
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

    class Meta:
        model = models.Regulation
        fields = [
            "id",
            "url",
            *BaseRegulationSerializer.Meta.fields,
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
