from datetime import datetime
from decimal import Decimal

from rest_framework import serializers

from common.serializers import TrackedModelSerializer
from common.serializers import TrackedModelSerializerMixin
from common.serializers import ValiditySerializerMixin
from common.serializers import deserialize_date
from common.serializers import serialize_date
from common.util import TaricDateRange
from common.validators import UpdateType
from geo_areas.serializers import GeographicalAreaSerializer
from measures.models.tracked_models import MeasurementUnit
from measures.unit_serializers import MeasurementUnitQualifierSerializer
from measures.unit_serializers import MeasurementUnitSerializer
from measures.unit_serializers import MonetaryUnitSerializer
from quotas import models


@TrackedModelSerializer.register_polymorphic_model
class QuotaOrderNumberSerializer(TrackedModelSerializerMixin, ValiditySerializerMixin):
    sid = serializers.IntegerField(min_value=1, max_value=99999999)

    class Meta:
        model = models.QuotaOrderNumber
        fields = [
            "id",
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
    TrackedModelSerializerMixin,
    ValiditySerializerMixin,
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
    TrackedModelSerializerMixin,
    ValiditySerializerMixin,
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
    TrackedModelSerializerMixin,
    ValiditySerializerMixin,
):
    class Meta:
        model = models.QuotaDefinition
        fields = [
            "sid",
            "order_number",
        ]


class QuotaDefinitionImporterSerializer(
    TrackedModelSerializerMixin,
    ValiditySerializerMixin,
):
    order_number = QuotaOrderNumberSerializer(required=False)
    sid = serializers.IntegerField()
    measurement_unit = MeasurementUnitSerializer(read_only=True)
    measurement_unit_qualifier = MeasurementUnitQualifierSerializer(read_only=True)
    monetary_unit = MonetaryUnitSerializer(read_only=True)

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
        many=True,
        read_only=True,
        required=False,
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


def serialize_duplicate_data(selected_definition):
    # returns a JSON dictionary of serialized definition data
    duplicate_data = {
        "initial_volume": str(selected_definition.initial_volume),
        "volume": str(selected_definition.volume),
        "measurement_unit_code": selected_definition.measurement_unit.code,
        "measurement_unit_abbreviation": selected_definition.measurement_unit.abbreviation,
        "start_date": serialize_date(selected_definition.valid_between.lower),
        "end_date": serialize_date(selected_definition.valid_between.upper),
        "status": False,
    }
    return duplicate_data


def deserialize_definition_data(self, definition):
    start_date = deserialize_date(definition["start_date"])
    end_date = deserialize_date(definition["end_date"])
    initial_volume = Decimal(definition["initial_volume"])
    vol = Decimal(definition["volume"])
    measurement_unit = MeasurementUnit.objects.get(
        code=definition["measurement_unit_code"],
    )
    sub_order_number = self.get_cleaned_data_for_step(self.QUOTA_ORDER_NUMBERS)[
        "sub_quota_order_number"
    ]
    valid_between = TaricDateRange(start_date, end_date)
    staged_data = {
        "volume": initial_volume,
        "initial_volume": vol,
        "measurement_unit": measurement_unit,
        "order_number": sub_order_number,
        "valid_between": valid_between,
        "update_type": UpdateType.CREATE,
        "maximum_precision": 3,
        "quota_critical_threshold": 90,
    }
    return staged_data
