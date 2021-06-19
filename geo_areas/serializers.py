from rest_framework import serializers

from common.serializers import TrackedModelSerializer
from common.serializers import TrackedModelSerializerMixin
from common.serializers import ValiditySerializerMixin
from common.serializers import ValidityStartSerializerMixin
from geo_areas import models


class GeographicalAreaDescriptionSerializer(
    ValidityStartSerializerMixin,
    TrackedModelSerializerMixin,
):
    class Meta:
        model = models.GeographicalAreaDescription
        fields = [
            "sid",
            "description",
            "validity_start",
            "start_date",
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
            "start_date",
            "end_date",
            "update_type",
        ]


class GeographicalAreaImporterSerializer(
    ValiditySerializerMixin,
    TrackedModelSerializerMixin,
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
            "start_date",
            "end_date",
            "update_type",
        ]


class GeographicalAreaBasicSerializer(
    ValiditySerializerMixin,
    TrackedModelSerializerMixin,
):
    class Meta:
        model = models.GeographicalArea
        fields = [
            "area_id",
            "sid",
            "area_code",
            "valid_between",
            "start_date",
            "end_date",
        ]


@TrackedModelSerializer.register_polymorphic_model
class GeographicalAreaDescriptionTaricSerializer(
    ValidityStartSerializerMixin,
    TrackedModelSerializerMixin,
):
    described_geographicalarea = GeographicalAreaBasicSerializer(read_only=True)

    class Meta:
        model = models.GeographicalAreaDescription
        fields = [
            "sid",
            "described_geographicalarea",
            "description",
            "validity_start",
            "start_date",
            "update_type",
        ]


class GeographicalAreaDescriptionImporterSerializer(
    ValidityStartSerializerMixin,
    TrackedModelSerializerMixin,
):
    sid = serializers.IntegerField()
    described_geographicalarea = GeographicalAreaBasicSerializer(read_only=True)

    class Meta:
        model = models.GeographicalAreaDescription
        fields = [
            "sid",
            "description",
            "described_geographicalarea",
            "validity_start",
            "start_date",
            "update_type",
        ]


@TrackedModelSerializer.register_polymorphic_model
class GeographicalMembershipSerializer(
    ValiditySerializerMixin,
    TrackedModelSerializerMixin,
):
    geo_group = GeographicalAreaSerializer(read_only=True)
    member = GeographicalAreaSerializer(read_only=True)

    class Meta:
        model = models.GeographicalMembership
        fields = [
            "geo_group",
            "member",
            "start_date",
            "end_date",
            "update_type",
            "valid_between",
        ]
