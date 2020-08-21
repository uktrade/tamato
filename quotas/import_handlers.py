import re

from common.validators import UpdateType
from footnotes.models import Footnote
from footnotes.models import FootnoteType
from importer.handlers import ElementHandler
from importer.handlers import TextElement
from importer.handlers import ValidityMixin
from importer.handlers import Writable
from importer.namespaces import Tag
from importer.taric import Record
from quotas import serializers


@Record.register_child("quota_order_number")
class QuotaOrderNumber(ValidityMixin, Writable, ElementHandler):
    serializer_class = serializers.QuotaOrderNumberSerializer

    tag = Tag("quota.order.number")
    sid = TextElement(Tag("quota.order.number.sid"))
    order_number = TextElement(Tag("quota.order.number.id"))

    def clean(self):
        super().clean()
        # mechanism and category do not occur in TARIC3, can we calculate them?
        self.data["mechanism"] = "0"
        self.data["category"] = "1"


@Record.register_child("quota_order_number_origin")
class QuotaOrderNumberOrigin(ValidityMixin, Writable, ElementHandler):
    serializer_class = serializers.QuotaOrderNumberOriginSerializer

    tag = Tag("quota.order.number.origin")
    sid = TextElement(Tag("quota.order.number.origin.sid"))
    order_number_sid = TextElement(Tag("quota.order.number.sid"))
    geographical_area_id = TextElement(Tag("geographical.area.id"))
    geographical_area_sid = TextElement(Tag("geographical.area.sid"))


@Record.register_child("quota_order_number_origin_exclusion")
class QuotaOrderNumberOriginExclusion(Writable, ElementHandler):
    serializer_class = serializers.QuotaOrderNumberOriginExclusionSerializer

    tag = Tag("quota.order.number.origin.exclusions")
    origin_sid = TextElement(Tag("quota.order.number.origin.sid"))
    excluded_geographical_area_sid = TextElement(Tag("excluded.geographical.area.sid"))


@Record.register_child("quota_definition")
class QuotaDefinition(Writable, ValidityMixin, ElementHandler):
    serializer_class = serializers.QuotaDefinitionSerializer

    tag = Tag("quota.definition")
    sid = TextElement(Tag("quota.definition.sid"))
    order_number = TextElement(Tag("quota.order.number.id"))
    order_number_sid = TextElement(Tag("quota.order.number.sid"))
    volume = TextElement(Tag("volume"))
    initial_volume = TextElement(Tag("initial.volume"))
    monetary_unit_code = TextElement(Tag("monetary.unit.code"))
    measurement_unit_code = TextElement(Tag("measurement.unit.code"))
    measurement_unit_qualifier_code = TextElement(
        Tag("measurement.unit.qualifier.code")
    )
    maximum_precision = TextElement(Tag("maximum.precision"))
    critical_state = TextElement(Tag("critical.state"))
    critical_threshold = TextElement(Tag("critical.threshold"))
    description = TextElement(Tag("description"))


@Record.register_child("quota_association")
class QuotaAssociation(Writable, ElementHandler):
    serializer_class = serializers.QuotaAssociationSerializer

    tag = Tag("quota.association")
    main_quota_sid = TextElement(Tag("main.quota.definition.sid"))
    sub_quota_sid = TextElement(Tag("sub.quota.definition.sid"))
    relation_type = TextElement(Tag("relation.type"))
    coefficient = TextElement(Tag("coefficient"))


@Record.register_child("quota_blocking_period")
class QuotaBlockingPeriod(Writable, ElementHandler):
    serializer_class = serializers.QuotaBlockingSerializer

    tag = Tag("quota.blocking.period")
    sid = TextElement(Tag("quota.blocking.period.sid"))
    quota_definition_sid = TextElement(Tag("quota.definition.sid"))
    start_date = TextElement(Tag("blocking.start.date"))
    end_date = TextElement(Tag("blocking.end.date"))
    description = TextElement(Tag("description"))


@Record.register_child("quota_suspension_period")
class QuotaSuspensionPeriod(Writable, ElementHandler):
    serializer_class = serializers.QuotaSuspensionSerializer

    tag = Tag("quota.suspension.period")
    sid = TextElement(Tag("quota.suspension.period.sid"))
    quota_definition_sid = TextElement(Tag("quota.definition.sid"))
    start_date = TextElement(Tag("suspension.start.date"))
    end_date = TextElement(Tag("suspension.end.date"))
    description = TextElement(Tag("description"))


class RegexTag(Tag):
    def __init__(self, pattern):
        super().__init__(pattern)
        self.pattern = re.compile(pattern)

    def __eq__(self, other):
        if isinstance(other, Tag):
            return self.pattern.match(str(other))

        return self.pattern.match(other)


@Record.register_child("quota_balance_event")
class QuotaBalanceEvent(Writable, ElementHandler):
    serializer_class = serializers.QuotaEventSerializer

    tag = RegexTag(r"quota.([a-z.]+).event")
    quota_definition_sid = TextElement(Tag("quota.definition.sid"))
    occurrence_timestamp = TextElement(Tag("occurrence.timestamp"))

    _additional_components = {
        # balance event
        TextElement(Tag("old.balance")): "old.balance",
        TextElement(Tag("new.balance")): "new.balance",
        TextElement(Tag("imported.amount")): "imported.amount",
        TextElement(
            Tag("last.import.date.in.allocation")
        ): "last.import.date.in.allocation",
        # unblocking event
        TextElement(Tag("unblocking.date")): "unblocking.date",
        # critical event
        TextElement(Tag("critical.state")): "critical.state",
        TextElement(Tag("critical.state.change.date")): "critical.state.change.date",
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
            Tag("target.quota.definintion.sid")
        ): "target.quota.definintion.sid",
    }

    def clean(self):
        json_data = self.data.copy()
        if "quota_definition_sid" in json_data:
            del json_data["quota_definition_sid"]
        if "occurrence_timestamp" in json_data:
            del json_data["occurrence_timestamp"]
        self.data["data"] = json_data
