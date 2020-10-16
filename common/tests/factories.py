"""Factory classes for BDD tests."""
import random
import string
from decimal import Decimal
from itertools import product

import factory.fuzzy

from common.tests.models import TestModel1
from common.tests.models import TestModel2
from common.tests.util import Dates
from common.validators import ApplicabilityCode
from common.validators import UpdateType
from measures.validators import DutyExpressionId
from measures.validators import ImportExportCode
from measures.validators import MeasureTypeCombination
from measures.validators import OrderNumberCaptureCode
from quotas.validators import QuotaEventType
from workbaskets.validators import WorkflowStatus


def short_description():
    return factory.Faker("text", max_nb_chars=500)


def string_generator(length=1, characters=string.ascii_uppercase + string.digits):
    g = product(characters, repeat=length)
    return lambda *_: "".join(next(g))


def string_sequence(length=1, characters=string.ascii_uppercase + string.digits):
    return factory.Sequence(string_generator(length, characters))


def numeric_sid():
    return factory.Sequence(lambda x: x + 1)


def date_ranges(name):
    return factory.LazyFunction(lambda: getattr(Dates(), name))


class ValidityFactoryMixin(factory.django.DjangoModelFactory):
    valid_between = date_ranges("no_end")


class UserFactory(factory.django.DjangoModelFactory):
    """User factory."""

    class Meta:
        model = "auth.User"

    username = factory.sequence(lambda n: f"{factory.Faker('name')}{n}")


class WorkBasketFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "workbaskets.WorkBasket"

    author = factory.SubFactory(UserFactory)
    title = factory.Faker("text", max_nb_chars=255)


class ApprovedWorkBasketFactory(WorkBasketFactory):
    class Meta:
        model = "workbaskets.WorkBasket"

    approver = factory.SubFactory(UserFactory)
    status = WorkflowStatus.READY_FOR_EXPORT


class TransactionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "workbaskets.Transaction"

    workbasket = factory.SubFactory(ApprovedWorkBasketFactory)


class TrackedModelMixin(factory.django.DjangoModelFactory):
    workbasket = factory.SubFactory(WorkBasketFactory)
    update_type = UpdateType.UPDATE.value


class FootnoteTypeFactory(TrackedModelMixin, ValidityFactoryMixin):
    """FootnoteType factory."""

    class Meta:
        model = "footnotes.FootnoteType"

    footnote_type_id = string_sequence(2, characters=string.ascii_uppercase)
    application_code = 2
    description = short_description()


class FootnoteFactory(TrackedModelMixin, ValidityFactoryMixin):
    """Footnote factory."""

    class Meta:
        model = "footnotes.Footnote"

    footnote_id = string_sequence(length=3, characters=string.digits)
    footnote_type = factory.SubFactory(FootnoteTypeFactory)


class FootnoteDescriptionFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "footnotes.FootnoteDescription"

    description = short_description()
    described_footnote = factory.SubFactory(FootnoteFactory)
    description_period_sid = numeric_sid()


class RegulationGroupFactory(TrackedModelMixin):
    class Meta:
        model = "regulations.Group"

    group_id = string_sequence(3, characters=string.ascii_uppercase)
    description = short_description()
    valid_between = date_ranges("no_end")


class RegulationFactory(TrackedModelMixin):
    class Meta:
        model = "regulations.Regulation"

    regulation_id = factory.Sequence(lambda n: f"R{Dates().now:%y}{n:04d}0")
    approved = True
    role_type = 1
    valid_between = factory.LazyAttribute(
        lambda o: Dates().no_end if o.role_type == 1 else None
    )
    community_code = factory.LazyAttribute(lambda o: 1 if o.role_type == 1 else None)
    regulation_group = factory.LazyAttribute(
        lambda o: RegulationGroupFactory() if o.role_type == 1 else None
    )


class GeographicalAreaFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "geo_areas.GeographicalArea"

    sid = numeric_sid()
    area_id = string_sequence(4)
    area_code = factory.LazyFunction(lambda: random.randint(0, 2))


class GeographicalMembershipFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "geo_areas.GeographicalMembership"

    geo_group = factory.SubFactory(GeographicalAreaFactory, area_code=1)
    member = factory.SubFactory(
        GeographicalAreaFactory,
        area_code=factory.fuzzy.FuzzyChoice([0, 2]),
    )


class GeographicalAreaDescriptionFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "geo_areas.GeographicalAreaDescription"

    sid = numeric_sid()
    area = factory.SubFactory(GeographicalAreaFactory)
    description = short_description()


class CertificateTypeFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "certificates.CertificateType"

    sid = string_sequence(1)
    description = short_description()


class CertificateFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "certificates.Certificate"

    certificate_type = factory.SubFactory(CertificateTypeFactory)
    sid = string_sequence(3)


class CertificateDescriptionFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "certificates.CertificateDescription"

    sid = numeric_sid()

    described_certificate = factory.SubFactory(CertificateFactory)
    description = short_description()


class TestModel1Factory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = TestModel1

    name = factory.Faker("text", max_nb_chars=24)
    sid = numeric_sid()


class TestModel2Factory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = TestModel2

    description = factory.Faker("text", max_nb_chars=24)
    custom_sid = numeric_sid()


class AdditionalCodeTypeFactory(TrackedModelMixin, ValidityFactoryMixin):
    """AdditionalCodeType factory."""

    class Meta:
        model = "additional_codes.AdditionalCodeType"

    sid = string_sequence(1)
    description = short_description()
    application_code = 1


class AdditionalCodeFactory(TrackedModelMixin, ValidityFactoryMixin):
    """AdditionalCode factory."""

    class Meta:
        model = "additional_codes.AdditionalCode"

    sid = numeric_sid()
    type = factory.SubFactory(AdditionalCodeTypeFactory)
    code = string_sequence(3)


class AdditionalCodeDescriptionFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "additional_codes.AdditionalCodeDescription"

    description_period_sid = numeric_sid()
    described_additional_code = factory.SubFactory(AdditionalCodeFactory)
    description = short_description()


class SimpleGoodsNomenclatureFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "commodities.GoodsNomenclature"

    sid = numeric_sid()
    item_id = string_sequence(10, characters=string.digits)
    suffix = "80"
    statistical = False


class GoodsNomenclatureFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "commodities.GoodsNomenclature"

    sid = numeric_sid()
    item_id = string_sequence(10, characters=string.digits)
    suffix = "80"
    statistical = False

    indent = factory.RelatedFactory(
        "common.tests.factories.GoodsNomenclatureIndentFactory",
        factory_related_name="indented_goods_nomenclature",
        workbasket=factory.SelfAttribute("..workbasket"),
        valid_between=factory.SelfAttribute("..valid_between"),
    )

    description = factory.RelatedFactory(
        "common.tests.factories.GoodsNomenclatureDescriptionFactory",
        factory_related_name="described_goods_nomenclature",
        workbasket=factory.SelfAttribute("..workbasket"),
        valid_between=factory.SelfAttribute("..valid_between"),
    )


indent_path_generator = string_generator(4)


def build_indent_path(good):
    parent = good.parent
    if parent:
        return parent.path + indent_path_generator()
    return indent_path_generator()


class GoodsNomenclatureIndentFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "commodities.GoodsNomenclatureIndent"
        exclude = ("parent",)

    parent = None

    path = factory.LazyAttribute(build_indent_path)
    depth = factory.LazyAttribute(lambda o: len(o.path) // 4)

    sid = numeric_sid()
    indented_goods_nomenclature = factory.SubFactory(SimpleGoodsNomenclatureFactory)


class GoodsNomenclatureDescriptionFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "commodities.GoodsNomenclatureDescription"

    sid = numeric_sid()
    described_goods_nomenclature = factory.SubFactory(GoodsNomenclatureFactory)
    description = short_description()


class FootnoteAssociationGoodsNomenclatureFactory(
    TrackedModelMixin, ValidityFactoryMixin
):
    class Meta:
        model = "commodities.FootnoteAssociationGoodsNomenclature"

    goods_nomenclature = factory.SubFactory(GoodsNomenclatureFactory)
    associated_footnote = factory.SubFactory(FootnoteFactory)


class QuotaOrderNumberFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "quotas.QuotaOrderNumber"

    sid = numeric_sid()
    order_number = string_sequence(6, characters=string.digits)
    mechanism = 0
    category = 0

    origin = factory.RelatedFactory(
        "common.tests.factories.QuotaOrderNumberOriginFactory",
        factory_related_name="order_number",
        valid_between=factory.SelfAttribute("..valid_between"),
        workbasket=factory.SelfAttribute("..workbasket"),
    )


class QuotaOrderNumberOriginFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "quotas.QuotaOrderNumberOrigin"

    sid = numeric_sid()
    order_number = factory.SubFactory(QuotaOrderNumberFactory)
    geographical_area = factory.SubFactory(GeographicalAreaFactory)


class QuotaOrderNumberOriginExclusionFactory(TrackedModelMixin):
    class Meta:
        model = "quotas.QuotaOrderNumberOriginExclusion"

    origin = factory.SubFactory(QuotaOrderNumberOriginFactory)
    excluded_geographical_area = factory.SubFactory(GeographicalAreaFactory)


class QuotaDefinitionFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "quotas.QuotaDefinition"

    sid = numeric_sid()
    order_number = factory.SubFactory(QuotaOrderNumberFactory)
    volume = 0
    initial_volume = 0
    maximum_precision = 0
    quota_critical = False
    quota_critical_threshold = 80
    description = short_description()


class QuotaAssociationFactory(TrackedModelMixin):
    class Meta:
        model = "quotas.QuotaAssociation"

    main_quota = factory.SubFactory(QuotaDefinitionFactory)
    sub_quota = factory.SubFactory(QuotaDefinitionFactory)
    sub_quota_relation_type = factory.fuzzy.FuzzyChoice(["EQ", "NM"])
    coefficient = Decimal("1.00000")


class QuotaSuspensionFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "quotas.QuotaSuspension"

    sid = numeric_sid()
    quota_definition = factory.SubFactory(QuotaDefinitionFactory)
    description = short_description()
    valid_between = date_ranges("normal")


class QuotaBlockingFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "quotas.QuotaBlocking"

    sid = numeric_sid()
    quota_definition = factory.SubFactory(QuotaDefinitionFactory)
    blocking_period_type = factory.fuzzy.FuzzyChoice(range(1, 9))
    valid_between = date_ranges("normal")


class QuotaEventFactory(TrackedModelMixin):
    class Meta:
        model = "quotas.QuotaEvent"

    subrecord_code = factory.fuzzy.FuzzyChoice(QuotaEventType.values)
    quota_definition = factory.SubFactory(QuotaDefinitionFactory)
    occurrence_timestamp = factory.LazyFunction(lambda: Dates().now)

    @factory.lazy_attribute
    def data(self):
        now = "{:%Y-%m-%d}".format(Dates().now)
        if self.subrecord_code == "00":
            return {
                "old.balance": 0.0,
                "new.balance": 0.0,
                "imported.amount": 0.0,
                "last.import.date.in.allocation": now,
            }
        if self.subrecord_code == "05":
            return {
                "unblocking.date": now,
            }
        if self.subrecord_code == "10":
            return {
                "critical.state": "Y",
                "critical.state.change.date": now,
            }
        if self.subrecord_code == "15":
            return {
                "exhaustion.date": now,
            }
        if self.subrecord_code == "20":
            return {
                "reopening.date": now,
            }
        if self.subrecord_code == "25":
            return {
                "unsuspension.date": now,
            }
        if self.subrecord_code == "30":
            return {
                "transfer.date": now,
                "quota.closed": "Y",
                "transferred.amount": 0.0,
                "target.quota.definition.sid": 1,
            }


class MeasureTypeSeriesFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "measures.MeasureTypeSeries"

    sid = string_sequence(2, characters=string.ascii_uppercase)
    measure_type_combination = factory.fuzzy.FuzzyChoice(MeasureTypeCombination.values)
    description = short_description()


class MeasurementUnitFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "measures.MeasurementUnit"

    code = string_sequence(3, characters=string.ascii_uppercase)
    description = short_description()


class MeasurementUnitQualifierFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "measures.MeasurementUnitQualifier"

    code = string_sequence(1, characters=string.ascii_uppercase)
    description = short_description()


class MeasurementFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "measures.Measurement"

    measurement_unit = factory.SubFactory(MeasurementUnitFactory)
    measurement_unit_qualifier = factory.SubFactory(MeasurementUnitQualifierFactory)


class MonetaryUnitFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "measures.MonetaryUnit"

    code = string_sequence(3, characters=string.ascii_uppercase)
    description = short_description()


class DutyExpressionFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "measures.DutyExpression"

    sid = factory.fuzzy.FuzzyChoice(DutyExpressionId.values)
    duty_amount_applicability_code = ApplicabilityCode.PERMITTED
    measurement_unit_applicability_code = ApplicabilityCode.PERMITTED
    monetary_unit_applicability_code = ApplicabilityCode.PERMITTED
    description = short_description()


class MeasureTypeFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "measures.MeasureType"

    sid = string_sequence(3, characters=string.ascii_uppercase)
    trade_movement_code = factory.fuzzy.FuzzyChoice(ImportExportCode.values)
    priority_code = factory.fuzzy.FuzzyChoice(range(1, 10))
    measure_component_applicability_code = factory.fuzzy.FuzzyChoice(
        ApplicabilityCode.values
    )
    order_number_capture_code = OrderNumberCaptureCode.NOT_PERMITTED
    measure_explosion_level = factory.fuzzy.FuzzyChoice(range(2, 11, 2))
    description = short_description()
    measure_type_series = factory.SubFactory(MeasureTypeSeriesFactory)


class AdditionalCodeTypeMeasureTypeFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "measures.AdditionalCodeTypeMeasureType"

    measure_type = factory.SubFactory(MeasureTypeFactory)
    additional_code_type = factory.SubFactory(AdditionalCodeTypeFactory)


class MeasureConditionCodeFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "measures.MeasureConditionCode"

    code = string_sequence(2, characters=string.ascii_uppercase)
    description = short_description()


class MeasureActionFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "measures.MeasureAction"

    code = factory.Faker("random_int", min=1, max=999)
    description = short_description()


class MeasureFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "measures.Measure"

    sid = numeric_sid()
    measure_type = factory.SubFactory(MeasureTypeFactory)
    geographical_area = factory.SubFactory(GeographicalAreaFactory)
    goods_nomenclature = factory.SubFactory(
        GoodsNomenclatureFactory,
        workbasket=factory.SelfAttribute("..workbasket"),
    )
    additional_code = None
    order_number = None
    reduction = factory.Faker("random_int", min=1, max=3)
    generating_regulation = factory.SubFactory(RegulationFactory)
    stopped = False
    export_refund_nomenclature_sid = None

    @factory.lazy_attribute
    def terminating_regulation(self):
        if self.valid_between.upper is None:
            return None
        return self.generating_regulation


class MeasureComponentFactory(TrackedModelMixin):
    class Meta:
        model = "measures.MeasureComponent"

    component_measure = factory.SubFactory(MeasureFactory)
    duty_expression = factory.SubFactory(DutyExpressionFactory)
    duty_amount = None
    monetary_unit = None
    component_measurement = None


class MeasureConditionFactory(TrackedModelMixin):
    class Meta:
        model = "measures.MeasureCondition"

    sid = numeric_sid()
    dependent_measure = factory.SubFactory(MeasureFactory)
    condition_code = factory.SubFactory(MeasureConditionCodeFactory)
    component_sequence_number = factory.Faker("random_int", min=1, max=999)
    duty_amount = factory.Faker("pydecimal", left_digits=7, right_digits=3)
    monetary_unit = factory.SubFactory(MonetaryUnitFactory)
    condition_measurement = None
    action = factory.SubFactory(MeasureActionFactory)
    required_certificate = None


class MeasureConditionComponentFactory(TrackedModelMixin):
    class Meta:
        model = "measures.MeasureConditionComponent"

    condition = factory.SubFactory(MeasureConditionFactory)
    duty_expression = factory.SubFactory(DutyExpressionFactory)
    duty_amount = factory.Faker("pydecimal", left_digits=7, right_digits=3)
    monetary_unit = factory.SubFactory(MonetaryUnitFactory)
    condition_component_measurement = None


class MeasureExcludedGeographicalAreaFactory(TrackedModelMixin):
    class Meta:
        model = "measures.MeasureExcludedGeographicalArea"

    modified_measure = factory.SubFactory(MeasureFactory)
    excluded_geographical_area = factory.SubFactory(GeographicalAreaFactory)


class FootnoteAssociationMeasureFactory(TrackedModelMixin):
    class Meta:
        model = "measures.FootnoteAssociationMeasure"

    footnoted_measure = factory.SubFactory(MeasureFactory)
    associated_footnote = factory.SubFactory(FootnoteFactory)
