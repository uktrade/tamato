from datetime import datetime

from rest_framework import serializers

from common.serializers import TrackedModelSerializer
from common.serializers import TrackedModelSerializerMixin
from common.serializers import ValiditySerializerMixin
from geo_areas.serializers import GeographicalAreaSerializer
from measures.serializers import MeasurementUnitQualifierSerializer
from measures.serializers import MeasurementUnitSerializer
from measures.serializers import MonetaryUnitSerializer
from quotas import models


@TrackedModelSerializer.register_polymorphic_model
class QuotaOrderNumberSerializer(TrackedModelSerializerMixin, ValiditySerializerMixin):
    sid = serializers.IntegerField(min_value=1, max_value=99999999)

    class Meta:
        model = models.QuotaOrderNumber
        fields = [
            "sid",
            "order_number",
            "mechanism",
            "category",
            "valid_between",
            "update_type",
            "record_code",
            "subrecord_code",
            "taric_template",
            "start_date",
            "end_date",
        ]


@TrackedModelSerializer.register_polymorphic_model
class QuotaOrderNumberOriginSerializer(
    TrackedModelSerializerMixin, ValiditySerializerMixin
):
    sid = serializers.IntegerField()
    order_number = QuotaOrderNumberSerializer(read_only=True)
    geographical_area = GeographicalAreaSerializer(read_only=True)

    class Meta:
        model = models.QuotaOrderNumberOrigin
        fields = [
            "sid",
            "order_number",
            "geographical_area",
            "valid_between",
            "update_type",
            "record_code",
            "subrecord_code",
            "taric_template",
            "start_date",
            "end_date",
        ]


@TrackedModelSerializer.register_polymorphic_model
class QuotaOrderNumberOriginExclusionSerializer(
    TrackedModelSerializerMixin, ValiditySerializerMixin
):
    origin = QuotaOrderNumberOriginSerializer(read_only=True)
    excluded_geographical_area = GeographicalAreaSerializer(read_only=True)

    class Meta:
        model = models.QuotaOrderNumberOriginExclusion
        fields = [
            "origin",
            "excluded_geographical_area",
            "update_type",
            "record_code",
            "subrecord_code",
            "taric_template",
        ]


class SimpleQuotaDefinitionSerializer(
    TrackedModelSerializerMixin, ValiditySerializerMixin
):
    class Meta:
        model = models.QuotaDefinition
        fields = [
            "sid",
            "order_number",
        ]


class QuotaDefinitionImporterSerializer(
    TrackedModelSerializerMixin, ValiditySerializerMixin
):
    order_number = QuotaOrderNumberSerializer(required=False)
    sid = serializers.IntegerField()

    class Meta:
        model = models.QuotaDefinition
        fields = [
            "sid",
            "order_number",
            "volume",
            "initial_volume",
            "maximum_precision",
            "quota_critical",
            "quota_critical_threshold",
            "description",
            "update_type",
            "valid_between",
            "taric_template",
            "start_date",
            "end_date",
        ]


@TrackedModelSerializer.register_polymorphic_model
class QuotaDefinitionSerializer(TrackedModelSerializerMixin, ValiditySerializerMixin):
    order_number = QuotaOrderNumberSerializer(read_only=True)
    sid = serializers.IntegerField()
    measurement_unit = MeasurementUnitSerializer(read_only=True)
    measurement_unit_qualifier = MeasurementUnitQualifierSerializer(read_only=True)
    monetary_unit = MonetaryUnitSerializer(read_only=True)
    sub_quotas = SimpleQuotaDefinitionSerializer(
        many=True, read_only=True, required=False
    )

    class Meta:
        model = models.QuotaDefinition
        fields = [
            "sid",
            "order_number",
            "volume",
            "initial_volume",
            "maximum_precision",
            "measurement_unit",
            "measurement_unit_qualifier",
            "monetary_unit",
            "quota_critical",
            "quota_critical_threshold",
            "description",
            "sub_quotas",
            "valid_between",
            "update_type",
            "record_code",
            "subrecord_code",
            "taric_template",
            "start_date",
            "end_date",
        ]


@TrackedModelSerializer.register_polymorphic_model
class QuotaAssociationSerializer(TrackedModelSerializerMixin):
    main_quota = SimpleQuotaDefinitionSerializer(read_only=True)
    sub_quota = SimpleQuotaDefinitionSerializer(read_only=True)

    class Meta:
        model = models.QuotaAssociation
        fields = [
            "main_quota",
            "sub_quota",
            "sub_quota_relation_type",
            "coefficient",
            "update_type",
            "record_code",
            "subrecord_code",
            "taric_template",
        ]


@TrackedModelSerializer.register_polymorphic_model
class QuotaSuspensionSerializer(TrackedModelSerializerMixin, ValiditySerializerMixin):
    quota_definition = SimpleQuotaDefinitionSerializer(read_only=True)
    sid = serializers.IntegerField()

    class Meta:
        model = models.QuotaSuspension
        fields = [
            "sid",
            "quota_definition",
            "description",
            "valid_between",
            "update_type",
            "record_code",
            "subrecord_code",
            "taric_template",
            "start_date",
            "end_date",
        ]


@TrackedModelSerializer.register_polymorphic_model
class QuotaBlockingSerializer(TrackedModelSerializerMixin, ValiditySerializerMixin):
    blocking_period_type = serializers.IntegerField()
    quota_definition = SimpleQuotaDefinitionSerializer(read_only=True)
    sid = serializers.IntegerField()

    class Meta:
        model = models.QuotaBlocking
        fields = [
            "sid",
            "quota_definition",
            "blocking_period_type",
            "description",
            "valid_between",
            "update_type",
            "record_code",
            "subrecord_code",
            "taric_template",
            "start_date",
            "end_date",
            "valid_between",
        ]


class QuotaEventImporterSerializer(TrackedModelSerializerMixin):
    quota_definition = SimpleQuotaDefinitionSerializer(required=False)

    class Meta:
        model = models.QuotaEvent
        fields = [
            "quota_definition",
            "occurrence_timestamp",
            "data",
            "update_type",
            "record_code",
            "subrecord_code",
            "taric_template",
        ]


@TrackedModelSerializer.register_polymorphic_model
class QuotaEventSerializer(TrackedModelSerializerMixin):
    date_format_string = "{:%Y-%m-%dT%H:%M:%S}"
    occurrence_timestamp = serializers.SerializerMethodField(read_only=True)
    quota_definition = SimpleQuotaDefinitionSerializer(read_only=True)

    def get_occurrence_timestamp(self, obj):
        if isinstance(obj.occurrence_timestamp, datetime):
            return self.date_format_string.format(obj.occurrence_timestamp)

    class Meta:
        model = models.QuotaEvent
        fields = [
            "quota_definition",
            "occurrence_timestamp",
            "data",
            "update_type",
            "record_code",
            "subrecord_code",
            "taric_template",
        ]
