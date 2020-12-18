from rest_framework import serializers

from common.serializers import TrackedModelSerializer
from common.serializers import TrackedModelSerializerMixin
from common.serializers import ValiditySerializerMixin
from geo_areas import models


class GeographicalAreaDescriptionSerializer(
    ValiditySerializerMixin, TrackedModelSerializerMixin
):
    class Meta:
        model = models.GeographicalAreaDescription
        fields = [
            "sid",
            "description",
            "valid_between",
            "record_code",
            "period_record_code",
            "subrecord_code",
            "period_subrecord_code",
            "taric_template",
            "start_date",
            "end_date",
        ]


class ParentGeographicalAreaSerializer(ValiditySerializerMixin):
    class Meta:
        model = models.GeographicalArea
        fields = ["sid"]


@TrackedModelSerializer.register_polymorphic_model
class GeographicalAreaSerializer(ValiditySerializerMixin, TrackedModelSerializerMixin):
    descriptions = GeographicalAreaDescriptionSerializer(many=True)
    parent = ParentGeographicalAreaSerializer(read_only=True)

    class Meta:
        model = models.GeographicalArea
        fields = [
            "area_id",
            "sid",
            "area_code",
            "descriptions",
            "valid_between",
            "parent",
            "record_code",
            "subrecord_code",
            "taric_template",
            "start_date",
            "end_date",
            "update_type",
        ]


class GeographicalAreaImporterSerializer(
    ValiditySerializerMixin, TrackedModelSerializerMixin
):
    sid = serializers.IntegerField()
    parent = ParentGeographicalAreaSerializer(read_only=True)

    class Meta:
        model = models.GeographicalArea
        fields = [
            "area_id",
            "sid",
            "area_code",
            "valid_between",
            "parent",
            "record_code",
            "subrecord_code",
            "taric_template",
            "start_date",
            "end_date",
            "update_type",
        ]


class GeographicalAreaBasicSerializer(
    ValiditySerializerMixin, TrackedModelSerializerMixin
):
    class Meta:
        model = models.GeographicalArea
        fields = [
            "area_id",
            "sid",
            "area_code",
            "valid_between",
            "record_code",
            "subrecord_code",
            "taric_template",
            "start_date",
            "end_date",
        ]


@TrackedModelSerializer.register_polymorphic_model
class GeographicalAreaDescriptionTaricSerializer(
    ValiditySerializerMixin, TrackedModelSerializerMixin
):
    area = GeographicalAreaBasicSerializer(read_only=True)

    class Meta:
        model = models.GeographicalAreaDescription
        fields = [
            "sid",
            "area",
            "description",
            "valid_between",
            "record_code",
            "period_record_code",
            "subrecord_code",
            "period_subrecord_code",
            "taric_template",
            "start_date",
            "end_date",
            "update_type",
        ]


class GeographicalAreaDescriptionImporterSerializer(
    ValiditySerializerMixin, TrackedModelSerializerMixin
):
    sid = serializers.IntegerField()
    area = GeographicalAreaBasicSerializer(read_only=True)

    class Meta:
        model = models.GeographicalAreaDescription
        fields = [
            "sid",
            "description",
            "area",
            "valid_between",
            "record_code",
            "period_record_code",
            "subrecord_code",
            "period_subrecord_code",
            "taric_template",
            "start_date",
            "end_date",
            "update_type",
        ]


@TrackedModelSerializer.register_polymorphic_model
class GeographicalMembershipSerializer(
    ValiditySerializerMixin, TrackedModelSerializerMixin
):
    geo_group = GeographicalAreaSerializer(read_only=True)
    member = GeographicalAreaSerializer(read_only=True)

    class Meta:
        model = models.GeographicalMembership
        fields = [
            "geo_group",
            "member",
            "record_code",
            "subrecord_code",
            "taric_template",
            "start_date",
            "end_date",
            "update_type",
            "valid_between",
        ]
