from importer.namespaces import RegexTag
from importer.namespaces import Tag
from importer.parsers import ElementParser
from importer.parsers import IntElement
from importer.parsers import InvalidDataError
from importer.parsers import TextElement
from importer.parsers import ValidityMixin
from importer.parsers import Writable
from importer.taric import RecordParser


@RecordParser.register_child("quota_order_number")
class QuotaOrderNumberParser(ValidityMixin, Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="quota.order.number" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="quota.order.number.sid" type="SID"/>
                    <xs:element name="quota.order.number.id" type="OrderNumber"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    record_code = "360"
    subrecord_code = "00"

    tag = Tag("quota.order.number")
    sid = TextElement(Tag("quota.order.number.sid"))
    order_number = TextElement(Tag("quota.order.number.id"))

    def clean(self):
        super().clean()
        # mechanism and category do not occur in TARIC3, can we calculate them?
        self.data["mechanism"] = "0"
        self.data["category"] = "1"


@RecordParser.register_child("quota_order_number_origin")
class QuotaOrderNumberOriginParser(ValidityMixin, Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="quota.order.number.origin" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="quota.order.number.origin.sid" type="SID"/>
                    <xs:element name="quota.order.number.sid" type="SID"/>
                    <xs:element name="geographical.area.id" type="GeographicalAreaId"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                    <xs:element name="geographical.area.sid" type="SID"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    record_code = "360"
    subrecord_code = "10"

    tag = Tag("quota.order.number.origin")

    sid = TextElement(Tag("quota.order.number.origin.sid"))
    order_number__sid = TextElement(Tag("quota.order.number.sid"))
    geographical_area__area_id = TextElement(Tag("geographical.area.id"))
    geographical_area__sid = TextElement(Tag("geographical.area.sid"))


@RecordParser.register_child("quota_order_number_origin_exclusion")
class QuotaOrderNumberOriginExclusionParser(Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="quota.order.number.origin.exclusions" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="quota.order.number.origin.sid" type="SID"/>
                    <xs:element name="excluded.geographical.area.sid" type="SID"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    record_code = "360"
    subrecord_code = "15"

    tag = Tag("quota.order.number.origin.exclusions")

    origin__sid = TextElement(Tag("quota.order.number.origin.sid"))
    excluded_geographical_area__sid = TextElement(Tag("excluded.geographical.area.sid"))


@RecordParser.register_child("quota_definition")
class QuotaDefinitionParser(ValidityMixin, Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="quota.definition" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="quota.definition.sid" type="SID"/>
                    <xs:element name="quota.order.number.id" type="OrderNumber"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                    <xs:element name="quota.order.number.sid" type="SID"/>
                    <xs:element name="volume" type="QuotaAmount"/>
                    <xs:element name="initial.volume" type="QuotaAmount"/>
                    <xs:element name="monetary.unit.code" type="MonetaryUnitCode" minOccurs="0"/>
                    <xs:element name="measurement.unit.code" type="MeasurementUnitCode" minOccurs="0"/>
                    <xs:element name="measurement.unit.qualifier.code" type="MeasurementUnitQualifierCode" minOccurs="0"/>
                    <xs:element name="maximum.precision" type="QuotaPrecision"/>
                    <xs:element name="critical.state" type="QuotaCriticalStateCode"/>
                    <xs:element name="critical.threshold" type="QuotaCriticalTreshold"/>
                    <xs:element name="description" type="ShortDescription" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    record_code = "370"
    subrecord_code = "00"

    tag = Tag("quota.definition")

    sid = TextElement(Tag("quota.definition.sid"))
    order_number__order_number = TextElement(Tag("quota.order.number.id"))
    order_number__sid = TextElement(Tag("quota.order.number.sid"))
    volume = TextElement(Tag("volume"))
    initial_volume = TextElement(Tag("initial.volume"))
    monetary_unit__code = TextElement(Tag("monetary.unit.code"))
    measurement_unit__code = TextElement(Tag("measurement.unit.code"))
    measurement_unit_qualifier__code = TextElement(
        Tag("measurement.unit.qualifier.code"),
    )
    maximum_precision = TextElement(Tag("maximum.precision"))
    quota_critical = TextElement(Tag("critical.state"))
    quota_critical_threshold = TextElement(Tag("critical.threshold"))
    description = TextElement(Tag("description"))

    def clean(self):
        super().clean()
        quota_critical = self.data.get("quota_critical")
        if quota_critical not in {"Y", "N"}:
            raise InvalidDataError(
                '"critical.state" tag must contain either "Y" or "N"',
            )
        self.data["quota_critical"] = quota_critical == "Y"


@RecordParser.register_child("quota_association")
class QuotaAssociationParser(Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="quota.association" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="main.quota.definition.sid" type="SID"/>
                    <xs:element name="sub.quota.definition.sid" type="SID"/>
                    <xs:element name="relation.type" type="RelationType"/>
                    <xs:element name="coefficient" type="QuotaCoefficient" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    record_code = "370"
    subrecord_code = "05"

    tag = Tag("quota.association")

    main_quota__sid = TextElement(Tag("main.quota.definition.sid"))
    sub_quota__sid = TextElement(Tag("sub.quota.definition.sid"))
    sub_quota_relation_type = TextElement(Tag("relation.type"))
    coefficient = TextElement(Tag("coefficient"))


@RecordParser.register_child("quota_blocking_period")
class QuotaBlockingParser(ValidityMixin, Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="quota.blocking.period" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="quota.blocking.period.sid" type="SID"/>
                    <xs:element name="quota.definition.sid" type="SID"/>
                    <xs:element name="blocking.start.date" type="Date"/>
                    <xs:element name="blocking.end.date" type="Date"/>
                    <xs:element name="blocking.period.type" type="QuotaBlockingPeriodType"/>
                    <xs:element name="description" type="ShortDescription" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    record_code = "370"
    subrecord_code = "10"

    tag = Tag("quota.blocking.period")

    sid = IntElement(Tag("quota.blocking.period.sid"))
    quota_definition__sid = IntElement(Tag("quota.definition.sid"))
    valid_between_lower = TextElement(Tag("blocking.start.date"))
    valid_between_upper = TextElement(Tag("blocking.end.date"))
    description = TextElement(Tag("description"))
    blocking_period_type = IntElement(Tag("blocking.period.type"))


@RecordParser.register_child("quota_suspension_period")
class QuotaSuspensionParser(ValidityMixin, Writable, ElementParser):
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="quota.suspension.period" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="quota.suspension.period.sid" type="SID"/>
                    <xs:element name="quota.definition.sid" type="SID"/>
                    <xs:element name="suspension.start.date" type="Date"/>
                    <xs:element name="suspension.end.date" type="Date"/>
                    <xs:element name="description" type="ShortDescription" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    record_code = "370"
    subrecord_code = "15"

    tag = Tag("quota.suspension.period")

    sid = IntElement(Tag("quota.suspension.period.sid"))
    quota_definition__sid = IntElement(Tag("quota.definition.sid"))
    valid_between_lower = TextElement(Tag("suspension.start.date"))
    valid_between_upper = TextElement(Tag("suspension.end.date"))
    description = TextElement(Tag("description"))


@RecordParser.register_child("quota_event")
class QuotaEventParser(Writable, ElementParser):
    """
    Could be one of any of the below:

    .. code:: XML

        <xs:element name="quota.balance.event" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="quota.definition.sid" type="SID"/>
                    <xs:element name="occurrence.timestamp" type="Timestamp"/>
                    <xs:element name="old.balance" type="QuotaAmount"/>
                    <xs:element name="new.balance" type="QuotaAmount"/>
                    <xs:element name="imported.amount" type="QuotaAmount"/>
                    <xs:element name="last.import.date.in.allocation" type="Date" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
        <xs:element name="quota.unblocking.event" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="quota.definition.sid" type="SID"/>
                    <xs:element name="occurrence.timestamp" type="Timestamp"/>
                    <xs:element name="unblocking.date" type="Date"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
        <xs:element name="quota.critical.event" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="quota.definition.sid" type="SID"/>
                    <xs:element name="occurrence.timestamp" type="Timestamp"/>
                    <xs:element name="critical.state" type="QuotaCriticalStateCode"/>
                    <xs:element name="critical.state.change.date" type="Date" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
        <xs:element name="quota.exhaustion.event" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="quota.definition.sid" type="SID"/>
                    <xs:element name="occurrence.timestamp" type="Timestamp"/>
                    <xs:element name="exhaustion.date" type="Date"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
        <xs:element name="quota.reopening.event" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="quota.definition.sid" type="SID"/>
                    <xs:element name="occurrence.timestamp" type="Timestamp"/>
                    <xs:element name="reopening.date" type="Date"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
        <xs:element name="quota.unsuspension.event" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="quota.definition.sid" type="SID"/>
                    <xs:element name="occurrence.timestamp" type="Timestamp"/>
                    <xs:element name="unsuspension.date" type="Date"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
        <xs:element name="quota.closed.and.transferred.event" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="quota.definition.sid" type="SID"/>
                    <xs:element name="occurrence.timestamp" type="Timestamp"/>
                    <!-- QTM148 CUSTD00029679 03/08/2013 CUST-DEV2  -->
                    <!--    <xs:element name="closing.date" type="Date"/> -->
                    <xs:element name="transfer.date" type="Date"/>
                    <xs:element name="quota.closed" type="QuotaClosedCode"/>
                    <!-- CUSTD00029679 - end -->
                    <xs:element name="transferred.amount" type="QuotaAmount"/>
                    <xs:element name="target.quota.definition.sid" type="SID"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    record_code = "375"
    subrecord_code = "subrecord_code"

    tag = RegexTag(r"quota.([a-z.]+).event")

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
        TextElement(Tag("target.quota.definition.sid")): "target.quota.definition.sid",
    }

    def clean(self):
        json_data = self.data.copy()
        if "quota_definition_sid" in json_data:
            del json_data["quota_definition_sid"]
        if "occurrence_timestamp" in json_data:
            del json_data["occurrence_timestamp"]
        self.data["data"] = json_data
        self.data["subrecord_code"] = self.parent.subrecord_code.data
