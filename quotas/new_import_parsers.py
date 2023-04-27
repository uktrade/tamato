from datetime import date

from importer.namespaces import Tag
from importer.new_parsers import NewElementParser
from importer.parsers import ElementParser
from importer.parsers import NewValidityMixin
from importer.parsers import NewWritable
from importer.parsers import TextElement


class NewQuotaOrderNumberParser(NewElementParser, NewValidityMixin, NewWritable):
    value_mapping = {
        "id": "order_number",
        "validity_start_date": "valid_between_lower",
        "validity_end_date": "valid_between_upper",
    }

    xml_object_tag = "quota.order.number"
    record_code = "360"
    subrecord_code = "00"

    sid: str = None
    order_number: str = None
    valid_between_lower: date = None
    valid_between_upper: date = None


class NewQuotaOrderNumberOriginParser(NewValidityMixin, NewWritable, NewElementParser):
    value_mapping = {
        "validity_start_date": "valid_between_lower",
        "validity_end_date": "valid_between_upper",
        "quota_order_number_sid": "order_number__sid",
        "geographical_area_id": "geographical_area__area_id",
        "geographical_area_sid": "geographical_area__sid",
    }

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
    xml_object_tag = "quota.order.number.origin.exclusions"
    record_code = "360"
    subrecord_code = "15"

    origin__sid: str = None
    excluded_geographical_area__sid: str = None


class NewQuotaDefinitionParser(NewValidityMixin, NewWritable, NewElementParser):
    value_mapping = {
        "validity_start_date": "valid_between_lower",
        "validity_end_date": "valid_between_upper",
    }

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
    xml_object_tag = "quota.association"
    record_code = "370"
    subrecord_code = "05"

    main_quota__sid: str = None
    sub_quota__sid: str = None
    sub_quota_relation_type: str = None
    coefficient: str = None


class NewQuotaBlockingParser(NewValidityMixin, NewWritable, NewElementParser):
    value_mapping = {
        "validity_start_date": "valid_between_lower",
        "validity_end_date": "valid_between_upper",
    }

    xml_object_tag = "quota.blocking.period"
    record_code = "370"
    subrecord_code = "10"

    sid: str = None
    quota_definition__sid: str = None
    valid_between_lower: str = None
    valid_between_upper: str = None
    blocking_period_type: str = None
    description: str = None


class NewQuotaSuspensionParser(NewValidityMixin, NewWritable, ElementParser):
    value_mapping = {
        "validity_start_date": "valid_between_lower",
        "validity_end_date": "valid_between_upper",
    }

    xml_object_tag = "quota.suspension.period"
    record_code = "370"
    subrecord_code = "15"

    sid: str = None
    quota_definition__sid: str = None
    valid_between_lower: str = None
    valid_between_upper: str = None
    description: str = None


class NewQuotaEventParser(NewWritable, NewElementParser):
    xml_object_tag = r"quota.([a-z.]+).event"
    record_code = "375"
    subrecord_code = "subrecord_code"

    quota_definition__sid: str = None
    occurrence_timestamp: str = None

    _additional_components = {
        # balance event
        TextElement(Tag("old.balance")): "old.balance",
        TextElement(Tag("new.balance")): "new.balance",
        TextElement(Tag("imported.amount")): "imported.amount",
        TextElement(
            Tag("last.import.date.in.allocation"),
        ): "last.import.date.in.allocation",
        # unblocking event
        TextElement(Tag("unblocking.date")): "unblocking.date",
        # critical event
        TextElement(Tag("critical.state")): "critical.state",
        TextElement(
            Tag("critical.state.change.date"),
        ): "critical.state.change.date",
        # exhaustion event
        TextElement(Tag("exhaustion.date")): "exhaustion.date",
        # reopening event
        TextElement(Tag("reopening.date")): "reopening.date",
        # unsuspension event
        TextElement(Tag("unsuspension.date")): "unsuspension.date",
        # closed and transferred event
        TextElement(Tag("transfer.date")): "transfer.date",
        TextElement(Tag("quota.closed")): "quota.closed",
        TextElement(Tag("transferred.amount")): "transferred.amount",
        TextElement(
            Tag("target.quota.definition.sid"),
        ): "target.quota.definition.sid",
    }
