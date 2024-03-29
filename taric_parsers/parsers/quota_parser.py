import json
from datetime import date
from datetime import datetime

from geo_areas.models import GeographicalArea
from measures.models import MeasurementUnit
from measures.models import MeasurementUnitQualifier
from measures.models import MonetaryUnit
from quotas.models import QuotaAssociation
from quotas.models import QuotaBlocking
from quotas.models import QuotaDefinition
from quotas.models import QuotaEvent
from quotas.models import QuotaOrderNumber
from quotas.models import QuotaOrderNumberOrigin
from quotas.models import QuotaOrderNumberOriginExclusion
from quotas.models import QuotaSuspension
from taric_parsers.parser_model_link import ModelLink
from taric_parsers.parser_model_link import ModelLinkField
from taric_parsers.parsers.taric_parser import BaseTaricParser


class QuotaOrderNumberParserV2(BaseTaricParser):
    model = QuotaOrderNumber

    value_mapping = {
        "quota_order_number_sid": "sid",
        "quota_order_number_id": "order_number",
        "validity_start_date": "valid_between_lower",
        "validity_end_date": "valid_between_upper",
    }

    non_taric_additional_fields = [
        "mechanism",
        "category",
    ]

    model_links = []

    record_code = "360"
    subrecord_code = "00"

    xml_object_tag = "quota.order.number"

    identity_fields = [
        "sid",
    ]

    sid: int = None
    order_number: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None

    # non taric properties
    mechanism: int = 0  # default
    category: int = 1  # default


class QuotaOrderNumberOriginParserV2(BaseTaricParser):
    model = QuotaOrderNumberOrigin

    value_mapping = {
        "quota_order_number_origin_sid": "sid",
        "quota_order_number_sid": "order_number__sid",
        "validity_start_date": "valid_between_lower",
        "validity_end_date": "valid_between_upper",
        "geographical_area_id": "geographical_area__area_id",
        "geographical_area_sid": "geographical_area__sid",
    }

    model_links = [
        ModelLink(
            QuotaOrderNumber,
            [
                ModelLinkField("order_number__sid", "sid"),
            ],
            "quota.order.number",
        ),
        ModelLink(
            GeographicalArea,
            [
                ModelLinkField("geographical_area__area_id", "area_id"),
                ModelLinkField("geographical_area__sid", "sid"),
            ],
            "geographical.area",
        ),
    ]

    xml_object_tag = "quota.order.number.origin"
    record_code = "360"
    subrecord_code = "10"

    identity_fields = [
        "sid",
    ]

    sid: int = None
    order_number__sid: int = None
    geographical_area__area_id: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None
    geographical_area__sid: int = None


class QuotaOrderNumberOriginExclusionParserV2(BaseTaricParser):
    model = QuotaOrderNumberOriginExclusion

    model_links = [
        ModelLink(
            QuotaOrderNumberOrigin,
            [
                ModelLinkField("origin__sid", "sid"),
            ],
            "quota.order.number.origin",
        ),
        ModelLink(
            GeographicalArea,
            [
                ModelLinkField("excluded_geographical_area__sid", "sid"),
            ],
            "geographical.area",
        ),
    ]

    value_mapping = {
        "quota_order_number_origin_sid": "origin__sid",
        "excluded_geographical_area_sid": "excluded_geographical_area__sid",
    }

    xml_object_tag = "quota.order.number.origin.exclusions"
    record_code = "360"
    subrecord_code = "15"

    identity_fields = [
        "origin__sid",
        "excluded_geographical_area__sid",
    ]

    origin__sid: int = None
    excluded_geographical_area__sid: int = None


class QuotaDefinitionParserV2(BaseTaricParser):
    model = QuotaDefinition

    model_links = [
        ModelLink(
            QuotaOrderNumber,
            [
                ModelLinkField("order_number__order_number", "order_number"),
                ModelLinkField("order_number__sid", "sid"),
            ],
            "quota.order.number",
        ),
        ModelLink(
            MonetaryUnit,
            [
                ModelLinkField("monetary_unit__code", "code"),
            ],
            "monetary.unit",
            True,  # optional
        ),
        ModelLink(
            MeasurementUnit,
            [
                ModelLinkField("measurement_unit__code", "code"),
            ],
            "measurement.unit",
            True,  # optional
        ),
        ModelLink(
            MeasurementUnitQualifier,
            [
                ModelLinkField("measurement_unit_qualifier__code", "code"),
            ],
            "measurement.unit.qualifier",
            True,  # optional
        ),
    ]

    xml_object_tag = "quota.definition"
    record_code = "370"
    subrecord_code = "00"

    value_mapping = {
        "quota_definition_sid": "sid",
        "quota_order_number_id": "order_number__order_number",
        "validity_start_date": "valid_between_lower",
        "validity_end_date": "valid_between_upper",
        "quota_order_number_sid": "order_number__sid",
        "monetary_unit_code": "monetary_unit__code",
        "measurement_unit_code": "measurement_unit__code",
        "measurement_unit_qualifier_code": "measurement_unit_qualifier__code",
        "critical_state": "quota_critical",
        "critical_threshold": "quota_critical_threshold",
    }

    identity_fields = [
        "sid",
        "order_number__sid",
    ]

    sid: int = None
    order_number__order_number: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None
    order_number__sid: int = None
    volume: int = None
    initial_volume: float = None
    monetary_unit__code: str = None
    measurement_unit__code: str = None
    measurement_unit_qualifier__code: str = None
    maximum_precision: int = None
    quota_critical: bool = None
    quota_critical_threshold: int = None
    description: str = None


class QuotaAssociationParserV2(BaseTaricParser):
    model = QuotaAssociation
    model_links = [
        ModelLink(
            QuotaDefinition,
            [
                ModelLinkField("main_quota__sid", "sid"),
            ],
            "quota.definition",
        ),
        ModelLink(
            QuotaDefinition,
            [
                ModelLinkField("sub_quota__sid", "sid"),
            ],
            "quota.definition",
        ),
    ]

    value_mapping = {
        "main_quota_definition_sid": "main_quota__sid",
        "sub_quota_definition_sid": "sub_quota__sid",
        "relation_type": "sub_quota_relation_type",
    }

    record_code = "370"
    subrecord_code = "05"

    xml_object_tag = "quota.association"

    identity_fields = [
        "main_quota__sid",
        "sub_quota__sid",
        "sub_quota_relation_type",
    ]

    main_quota__sid: int = None
    sub_quota__sid: int = None
    sub_quota_relation_type: str = None
    coefficient: float = None


class QuotaSuspensionParserV2(BaseTaricParser):
    model = QuotaSuspension

    model_links = [
        ModelLink(
            QuotaDefinition,
            [
                ModelLinkField("quota_definition__sid", "sid"),
            ],
            "quota.definition",
        ),
    ]

    value_mapping = {
        "suspension_start_date": "valid_between_lower",
        "suspension_end_date": "valid_between_upper",
        "quota_suspension_period_sid": "sid",
        "quota_definition_sid": "quota_definition__sid",
    }

    record_code = "370"
    subrecord_code = "15"

    xml_object_tag = "quota.suspension.period"

    identity_fields = [
        "sid",
    ]

    sid: int = None
    quota_definition__sid: int = None
    valid_between_lower: date = None
    valid_between_upper: date = None
    description: str = None


class QuotaBlockingParserV2(BaseTaricParser):
    model = QuotaBlocking

    xml_object_tag = "quota.blocking.period"
    record_code = "370"
    subrecord_code = "10"

    value_mapping = {
        "quota_blocking_period_sid": "sid",
        "quota_definition_sid": "quota_definition__sid",
        "blocking_start_date": "valid_between_lower",
        "blocking_end_date": "valid_between_upper",
    }

    model_links = [
        ModelLink(
            QuotaDefinition,
            [
                ModelLinkField("quota_definition__sid", "sid"),
            ],
            "quota.definition",
        ),
    ]

    identity_fields = [
        "sid",
    ]

    sid: int = None
    quota_definition__sid: int = None
    valid_between_lower: date = None
    valid_between_upper: date = None
    blocking_period_type: int = None
    description: str = None


class QuotaEventParserV2(BaseTaricParser):
    model = QuotaEvent

    model_links = [
        ModelLink(
            QuotaDefinition,
            [
                ModelLinkField("quota_definition__sid", "sid"),
            ],
            "quota.definition",
        ),
    ]

    data_fields = []

    record_code = "375"
    subrecord_code = "subrecord_code"

    xml_object_tag = "parent.quota.event"

    identity_fields = [
        "quota_definition__sid",
        "occurrence_timestamp",
    ]

    quota_definition__sid: str = None
    occurrence_timestamp: datetime = None

    @property
    def data(self):
        data_result = {}
        for field in self.__class__.data_fields:
            data_result[field.replace("_", ".")] = getattr(self, field)

        return json.dumps(data_result)


class QuotaBalanceEventParserV2(QuotaEventParserV2):
    xml_object_tag = "quota.balance.event"
    subrecord_code = "00"

    value_mapping = {
        "quota_definition_sid": "quota_definition__sid",
    }

    data_fields = [
        "new_balance",
        "old_balance",
        "imported_amount",
        "last_import_date_in_allocation",
    ]

    identity_fields = [
        "quota_definition__sid",
        "occurrence_timestamp",
    ]

    updates_allowed = False

    # data fields
    new_balance: str = None
    old_balance: str = None
    imported_amount: str = None
    last_import_date_in_allocation: str = None

    # fields
    quota_definition__sid: int = None
    occurrence_timestamp: datetime = None


class QuotaUnblockingEventParserV2(QuotaEventParserV2):
    subrecord_code = "05"

    value_mapping = {
        "quota_definition_sid": "quota_definition__sid",
    }

    xml_object_tag = "quota.unblocking.event"

    identity_fields = [
        "quota_definition__sid",
        "occurrence_timestamp",
    ]

    data_fields = [
        "unblocking_date",
    ]

    updates_allowed = False

    # data fields
    unblocking_date: str = None

    # fields
    quota_definition__sid: int = None
    occurrence_timestamp: datetime = None


class QuotaCriticalEventParserV2(QuotaEventParserV2):
    subrecord_code = "10"

    value_mapping = {
        "quota_definition_sid": "quota_definition__sid",
    }

    data_fields = [
        "critical_state",
        "critical_state_change_date",
    ]

    xml_object_tag = "quota.critical.event"

    identity_fields = [
        "quota_definition__sid",
        "occurrence_timestamp",
    ]

    updates_allowed = False

    # data fields
    critical_state: str = None
    critical_state_change_date: str = None

    # fields
    quota_definition__sid: int = None
    occurrence_timestamp: datetime = None


class QuotaExhaustionEventParserV2(QuotaEventParserV2):
    subrecord_code = "15"

    value_mapping = {
        "quota_definition_sid": "quota_definition__sid",
    }

    data_fields = [
        "exhaustion_date",
    ]

    xml_object_tag = "quota.exhaustion.event"

    identity_fields = [
        "quota_definition__sid",
        "occurrence_timestamp",
    ]

    updates_allowed = False

    # data fields
    exhaustion_date: str = None

    # fields
    quota_definition__sid: int = None
    occurrence_timestamp: datetime = None


class QuotaReopeningEventParserV2(QuotaEventParserV2):
    subrecord_code = "20"

    value_mapping = {
        "quota_definition_sid": "quota_definition__sid",
    }

    data_fields = [
        "reopening_date",
    ]

    xml_object_tag = "quota.reopening.event"

    identity_fields = [
        "quota_definition__sid",
        "occurrence_timestamp",
    ]

    updates_allowed = False

    # data fields
    reopening_date: str = None

    # fields
    quota_definition__sid: int = None
    occurrence_timestamp: datetime = None


class QuotaUnsuspensionEventParserV2(QuotaEventParserV2):
    subrecord_code = "25"

    value_mapping = {
        "quota_definition_sid": "quota_definition__sid",
    }

    data_fields = [
        "unsuspension_date",
    ]

    xml_object_tag = "quota.unsuspension.event"

    identity_fields = [
        "quota_definition__sid",
        "occurrence_timestamp",
    ]

    updates_allowed = False

    # data fields
    unsuspension_date: str = None

    # fields
    quota_definition__sid: int = None
    occurrence_timestamp: datetime = None


class QuotaClosedAndTransferredEventParserV2(QuotaEventParserV2):
    subrecord_code = "30"

    value_mapping = {
        "quota_definition_sid": "quota_definition__sid",
    }

    data_fields = [
        "quota_closed",
        "transferred_amount",
        "transfer_date",
        "target_quota_definition_sid",
    ]

    xml_object_tag = "quota.closed.and.transferred.event"

    identity_fields = [
        "quota_definition__sid",
        "occurrence_timestamp",
    ]

    updates_allowed = False

    # data fields
    quota_closed: str = None
    transferred_amount: str = None
    transfer_date: str = None
    target_quota_definition_sid: str = None

    # fields
    quota_definition__sid: int = None
    occurrence_timestamp: datetime = None
