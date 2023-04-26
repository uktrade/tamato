from datetime import date

from importer.namespaces import Tag
from importer.new_parsers import NewElementParser
from importer.parsers import BooleanElement
from importer.parsers import ElementParser
from importer.parsers import IntElement
from importer.parsers import NewValidityMixin
from importer.parsers import NewWritable
from importer.parsers import RangeLowerElement
from importer.parsers import RangeUpperElement
from importer.parsers import TextElement


class NewQuotaOrderNumberParser(NewElementParser, NewValidityMixin, NewWritable):
    xml_object_tag = "quota.order.number"
    record_code = "360"
    subrecord_code = "00"

    sid: str
    order_number: str
    valid_between_lower: date
    valid_between_upper: date


class NewQuotaOrderNumberOriginParser(NewValidityMixin, NewWritable, NewElementParser):
    xml_object_tag = "quota.order.number.origin"
    record_code = "360"
    subrecord_code = "10"
    tag: str

    sid: str
    order_number__sid: str
    geographical_area__area_id: str
    valid_between_lower: date
    valid_between_upper: date
    geographical_area__sid: str


class NewQuotaOrderNumberOriginExclusionParser(NewWritable, NewElementParser):
    xml_object_tag = "quota.order.number.origin.exclusions"
    record_code = "360"
    subrecord_code = "15"

    origin__sid = TextElement(Tag("quota.order.number.origin.sid"))
    excluded_geographical_area__sid = TextElement(
        Tag("excluded.geographical.area.sid"),
    )


class NewQuotaDefinitionParser(NewValidityMixin, NewWritable, NewElementParser):
    xml_object_tag = "quota.definition"
    record_code = "370"
    subrecord_code = "00"

    sid = TextElement(Tag("quota.definition.sid"))
    order_number__order_number = TextElement(Tag("quota.order.number.id"))
    valid_between_lower: date
    valid_between_upper: date
    order_number__sid = TextElement(Tag("quota.order.number.sid"))
    volume = TextElement(Tag("volume"))
    initial_volume = TextElement(Tag("initial.volume"))
    monetary_unit__code = TextElement(Tag("monetary.unit.code"))
    measurement_unit__code = TextElement(Tag("measurement.unit.code"))
    measurement_unit_qualifier__code = TextElement(
        Tag("measurement.unit.qualifier.code"),
    )
    maximum_precision = TextElement(Tag("maximum.precision"))
    quota_critical = BooleanElement(
        Tag("critical.state"),
        true_value="Y",
        false_value="N",
    )
    quota_critical_threshold = TextElement(Tag("critical.threshold"))
    description = TextElement(Tag("description"))


class NewQuotaAssociationParser(NewWritable, NewElementParser):
    xml_object_tag = "quota.association"
    record_code = "370"
    subrecord_code = "05"

    main_quota__sid = TextElement(Tag("main.quota.definition.sid"))
    sub_quota__sid = TextElement(Tag("sub.quota.definition.sid"))
    sub_quota_relation_type = TextElement(Tag("relation.type"))
    coefficient = TextElement(Tag("coefficient"))


class NewQuotaBlockingParser(NewValidityMixin, NewWritable, NewElementParser):
    xml_object_tag = "quota.blocking.period"
    record_code = "370"
    subrecord_code = "10"

    sid = IntElement(Tag("quota.blocking.period.sid"))
    quota_definition__sid = IntElement(Tag("quota.definition.sid"))
    valid_between_lower = RangeLowerElement(Tag("blocking.start.date"))
    valid_between_upper = RangeUpperElement(Tag("blocking.end.date"))
    blocking_period_type = IntElement(Tag("blocking.period.type"))
    description = TextElement(Tag("description"))


class NewQuotaSuspensionParser(NewValidityMixin, NewWritable, ElementParser):
    xml_object_tag = "quota.suspension.period"
    record_code = "370"
    subrecord_code = "15"

    sid = IntElement(Tag("quota.suspension.period.sid"))
    quota_definition__sid = IntElement(Tag("quota.definition.sid"))
    valid_between_lower = RangeLowerElement(Tag("suspension.start.date"))
    valid_between_upper = RangeUpperElement(Tag("suspension.end.date"))
    description = TextElement(Tag("description"))


class NewQuotaEventParser(NewWritable, NewElementParser):
    xml_object_tag = r"quota.([a-z.]+).event"
    record_code = "375"
    subrecord_code = "subrecord_code"

    quota_definition__sid = TextElement(Tag("quota.definition.sid"))
    occurrence_timestamp = TextElement(Tag("occurrence.timestamp"))

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
