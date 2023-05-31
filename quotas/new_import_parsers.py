from datetime import date

from importer.new_parsers import ModelLink
from importer.new_parsers import ModelLinkField
from importer.new_parsers import NewElementParser
from importer.parsers import NewValidityMixin
from importer.parsers import NewWritable
from quotas.import_handlers import *


class NewQuotaOrderNumberParser(NewElementParser, NewValidityMixin, NewWritable):
    model = models.QuotaOrderNumber

    value_mapping = {
        "id": "order_number",
        "validity_start_date": "valid_between_lower",
        "validity_end_date": "valid_between_upper",
    }

    model_links = []

    xml_object_tag = "quota.order.number"
    record_code = "360"
    subrecord_code = "00"

    sid: str = None
    order_number: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None


class NewQuotaOrderNumberOriginParser(NewValidityMixin, NewWritable, NewElementParser):
    model = models.QuotaOrderNumberOrigin

    value_mapping = {
        "validity_start_date": "valid_between_lower",
        "validity_end_date": "valid_between_upper",
        "quota_order_number_sid": "order_number__sid",
        "geographical_area_id": "geographical_area__area_id",
        "geographical_area_sid": "geographical_area__sid",
    }

    model_links = [
        ModelLink(
            models.QuotaOrderNumber,
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

    sid: str = None
    order_number__sid: str = None
    geographical_area__area_id: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None
    geographical_area__sid: str = None


class NewQuotaOrderNumberOriginExclusionParser(NewWritable, NewElementParser):
    model = models.QuotaOrderNumberOriginExclusion

    model_links = [
        # create dependency to quota order number origin
        ModelLink(
            models.QuotaOrderNumberOrigin,
            [
                ModelLinkField("origin__sid", "sid"),
            ],
            "quota.order.number.origin",
        ),
        # create dependency to geographical area
        ModelLink(
            GeographicalArea,
            [
                ModelLinkField("excluded_geographical_area__sid", "sid"),
            ],
            "geographical.area",
        ),
    ]

    xml_object_tag = "quota.order.number.origin.exclusions"
    record_code = "360"
    subrecord_code = "15"

    origin__sid: str = None
    excluded_geographical_area__sid: str = None


class NewQuotaDefinitionParser(NewValidityMixin, NewWritable, NewElementParser):
    model = models.QuotaDefinition
    value_mapping = {
        "validity_start_date": "valid_between_lower",
        "validity_end_date": "valid_between_upper",
    }

    model_links = [
        # create dependency to quota order number
        ModelLink(
            models.QuotaOrderNumber,
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
        # create optional dependency to MeasurementUnit
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

    sid: str = None
    order_number__order_number: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None
    order_number__sid: str = None
    volume: int = None
    initial_volume: str = None
    monetary_unit__code: str = None
    measurement_unit__code: str = None
    measurement_unit_qualifier__code: str = None
    maximum_precision: str = None
    quota_critical: str = None
    quota_critical_threshold: str = None
    description: str = None


class NewQuotaAssociationParser(NewWritable, NewElementParser):
    model = models.QuotaAssociation
    model_links = [
        # create dependency to QuotaDefinition (main quota)
        ModelLink(
            models.QuotaDefinition,
            [
                ModelLinkField("main_quota__sid", "sid"),
            ],
            "quota.definition",
        ),
        # create dependency to QuotaDefinition (sub quota)
        ModelLink(
            models.QuotaDefinition,
            [
                ModelLinkField("sub_quota__sid", "sid"),
            ],
            "quota.definition",
        ),
    ]

    xml_object_tag = "quota.association"
    record_code = "370"
    subrecord_code = "05"

    main_quota__sid: str = None
    sub_quota__sid: str = None
    sub_quota_relation_type: str = None
    coefficient: str = None


class NewQuotaSuspensionParser(NewValidityMixin, NewWritable, NewElementParser):
    model = models.QuotaSuspension

    value_mapping = {
        "validity_start_date": "valid_between_lower",
        "validity_end_date": "valid_between_upper",
    }

    # create dependency to QuotaDefinition
    model_links = [
        ModelLink(
            models.QuotaDefinition,
            [
                ModelLinkField("quota_definition__sid", "sid"),
            ],
            "quota.definition",
        ),
    ]

    xml_object_tag = "quota.suspension.period"
    record_code = "370"
    subrecord_code = "15"

    sid: str = None
    quota_definition__sid: str = None
    valid_between_lower: str = None
    valid_between_upper: str = None
    description: str = None


class NewQuotaBlockingParser(NewValidityMixin, NewWritable, NewElementParser):
    model = models.QuotaBlocking

    value_mapping = {
        "validity_start_date": "valid_between_lower",
        "validity_end_date": "valid_between_upper",
    }

    # create dependency to QuotaDefinition
    model_links = [
        ModelLink(
            models.QuotaDefinition,
            [
                ModelLinkField("quota_definition__sid", "sid"),
            ],
            "quota.definition",
        ),
    ]

    xml_object_tag = "quota.blocking.period"
    record_code = "370"
    subrecord_code = "10"

    sid: str = None
    quota_definition__sid: str = None
    valid_between_lower: str = None
    valid_between_upper: str = None
    blocking_period_type: str = None
    description: str = None


class NewQuotaEventParser(NewWritable, NewElementParser):
    # TODO: review all possible examples of quota events
    # handler = QuotaEventHandler
    model = models.QuotaEvent

    # create dependency to QuotaDefinition
    model_links = [
        ModelLink(
            models.QuotaDefinition,
            [
                ModelLinkField("quota_definition__sid", "sid"),
            ],
            "quota.definition",
        ),
    ]

    xml_object_tag = r"quota.([a-z.]+).event"
    record_code = "375"
    subrecord_code = "subrecord_code"

    quota_definition__sid: str = None
    occurrence_timestamp: str = None

    # _additional_components = {
    #     # balance event
    #     TextElement(Tag("old.balance")): "old.balance",
    #     TextElement(Tag("new.balance")): "new.balance",
    #     TextElement(Tag("imported.amount")): "imported.amount",
    #     TextElement(
    #         Tag("last.import.date.in.allocation"),
    #     ): "last.import.date.in.allocation",
    #     # unblocking event
    #     TextElement(Tag("unblocking.date")): "unblocking.date",
    #     # critical event
    #     TextElement(Tag("critical.state")): "critical.state",
    #     TextElement(
    #         Tag("critical.state.change.date"),
    #     ): "critical.state.change.date",
    #     # exhaustion event
    #     TextElement(Tag("exhaustion.date")): "exhaustion.date",
    #     # reopening event
    #     TextElement(Tag("reopening.date")): "reopening.date",
    #     # unsuspension event
    #     TextElement(Tag("unsuspension.date")): "unsuspension.date",
    #     # closed and transferred event
    #     TextElement(Tag("transfer.date")): "transfer.date",
    #     TextElement(Tag("quota.closed")): "quota.closed",
    #     TextElement(Tag("transferred.amount")): "transferred.amount",
    #     TextElement(
    #         Tag("target.quota.definition.sid"),
    #     ): "target.quota.definition.sid",
    # }
