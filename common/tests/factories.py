"""Factory classes for BDD tests."""
import string
from decimal import Decimal
from itertools import cycle
from itertools import product

import factory
from factory.fuzzy import FuzzyChoice

from common.models import TrackedModel
from common.tests.models import TestModel1
from common.tests.models import TestModel2
from common.tests.models import TestModel3
from common.tests.models import TestModelDescription1
from common.tests.util import Dates
from common.validators import ApplicabilityCode
from common.validators import UpdateType
from geo_areas.validators import AreaCode
from importer.models import ImporterChunkStatus
from measures.validators import DutyExpressionId
from measures.validators import ImportExportCode
from measures.validators import MeasureTypeCombination
from measures.validators import OrderNumberCaptureCode
from quotas.validators import QuotaEventType
from workbaskets.validators import WorkflowStatus


def short_description():
    return factory.Faker("text", max_nb_chars=500)


def string_generator(length=1, characters=string.ascii_uppercase + string.digits):
    g = cycle(product(characters, repeat=length))
    return lambda *_: "".join(next(g))[::-1]


def string_sequence(length=1, characters=string.ascii_uppercase + string.digits):
    return factory.Sequence(string_generator(length, characters))


def numeric_sid():
    return factory.Sequence(lambda x: x + 1)


def date_ranges(name):
    return factory.LazyFunction(lambda: getattr(Dates(), name))


class ValidityFactoryMixin(factory.django.DjangoModelFactory):
    valid_between = date_ranges("no_end")


class ValidityStartFactoryMixin(factory.django.DjangoModelFactory):
    validity_start = date_ranges("now")


class UserFactory(factory.django.DjangoModelFactory):
    """User factory."""

    class Meta:
        model = "auth.User"

    username = factory.sequence(lambda n: f"{factory.Faker('name')}{n}")


class UserGroupFactory(factory.django.DjangoModelFactory):
    """User Group factory."""

    class Meta:
        model = "auth.Group"

    name = factory.Faker("bs")


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
    transaction = factory.RelatedFactory(
        "common.tests.factories.TransactionFactory",
        factory_related_name="workbasket",
    )


class SimpleApprovedWorkBasketFactory(WorkBasketFactory):
    class Meta:
        model = "workbaskets.WorkBasket"

    approver = factory.SubFactory(UserFactory)
    status = WorkflowStatus.READY_FOR_EXPORT


class TransactionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "common.Transaction"

    order = factory.Sequence(lambda x: x + 1)
    import_transaction_id = factory.Sequence(lambda x: x + 1)
    workbasket = factory.SubFactory(SimpleApprovedWorkBasketFactory)
    composite_key = factory.Sequence(str)


ApprovedTransactionFactory = TransactionFactory


class UnapprovedTransactionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "common.Transaction"

    order = factory.Sequence(lambda x: x + 1)
    import_transaction_id = factory.Sequence(lambda x: x + 1)
    workbasket = factory.SubFactory(WorkBasketFactory)


class VersionGroupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "common.VersionGroup"


class TrackedModelMixin(factory.django.DjangoModelFactory):
    transaction = factory.SubFactory(TransactionFactory)
    update_type = UpdateType.CREATE.value
    version_group = factory.SubFactory(VersionGroupFactory)

    @classmethod
    def _after_postgeneration(cls, instance: TrackedModel, create, results=None):
        """Save again the instance if creating and at least one hook ran."""
        if create and results:
            # Some post-generation hooks ran, and may have modified us.
            instance.save(force_write=True)


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

    description = factory.RelatedFactory(
        "common.tests.factories.FootnoteDescriptionFactory",
        factory_related_name="described_footnote",
        transaction=factory.SelfAttribute("..transaction"),
        validity_start=factory.SelfAttribute("..valid_between.lower"),
    )


class FootnoteDescriptionFactory(TrackedModelMixin, ValidityStartFactoryMixin):
    class Meta:
        model = "footnotes.FootnoteDescription"

    description = short_description()
    described_footnote = factory.SubFactory(
        FootnoteFactory,
        description=None,
    )
    sid = numeric_sid()


class RegulationGroupFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "regulations.Group"

    group_id = string_sequence(3, characters=string.ascii_uppercase)
    description = short_description()


class RegulationFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "regulations.Regulation"

    regulation_id = factory.Sequence(lambda n: f"R{Dates().now:%y}{n:04d}0")
    approved = True
    role_type = 1
    valid_between = factory.LazyAttribute(
        lambda o: Dates().no_end if o.role_type == 1 else None,
    )
    community_code = 1
    regulation_group = factory.LazyAttribute(
        lambda o: RegulationGroupFactory(
            valid_between=o.valid_between,
            transaction=o.transaction,
        )
        if o.role_type == 1
        else None,
    )
    information_text = string_sequence(length=50)
    public_identifier = factory.sequence(lambda n: f"S.I. 2021/{n}")
    url = factory.sequence(lambda n: f"https://legislation.gov.uk/uksi/2021/{n}")


class BaseRegulationFactory(RegulationFactory):
    regulation_group = factory.SubFactory(RegulationGroupFactory)
    role_type = 1


class AmendmentFactory(TrackedModelMixin):
    class Meta:
        model = "regulations.Amendment"

    target_regulation = factory.SubFactory(RegulationFactory)
    enacting_regulation = factory.SubFactory(RegulationFactory)


class ExtensionFactory(TrackedModelMixin):
    class Meta:
        model = "regulations.Extension"

    target_regulation = factory.SubFactory(RegulationFactory)
    enacting_regulation = factory.SubFactory(RegulationFactory)


class SuspensionFactory(TrackedModelMixin):
    class Meta:
        model = "regulations.Suspension"

    target_regulation = factory.SubFactory(RegulationFactory)
    enacting_regulation = factory.SubFactory(RegulationFactory)


class TerminationFactory(TrackedModelMixin):
    class Meta:
        model = "regulations.Termination"

    target_regulation = factory.SubFactory(RegulationFactory)
    enacting_regulation = factory.SubFactory(RegulationFactory)

    effective_date = Dates().datetime_now


class ReplacementFactory(TrackedModelMixin):
    class Meta:
        model = "regulations.Replacement"

    target_regulation = factory.SubFactory(RegulationFactory)
    enacting_regulation = factory.SubFactory(RegulationFactory)
    measure_type_id = "AAAAAA"
    geographical_area_id = "GB"
    chapter_heading = "01"


class GeographicalAreaFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "geo_areas.GeographicalArea"

    sid = numeric_sid()
    area_id = string_sequence(4)
    area_code = FuzzyChoice([0, 2])

    description = factory.RelatedFactory(
        "common.tests.factories.GeographicalAreaDescriptionFactory",
        factory_related_name="described_geographicalarea",
        transaction=factory.SelfAttribute("..transaction"),
        validity_start=factory.SelfAttribute("..valid_between.lower"),
    )


class CountryFactory(GeographicalAreaFactory):
    area_code = 0


class GeoGroupFactory(GeographicalAreaFactory):
    area_code = 1


class RegionFactory(GeographicalAreaFactory):
    area_code = 2


class GeographicalMembershipFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "geo_areas.GeographicalMembership"

    geo_group = factory.SubFactory(GeoGroupFactory)
    member = factory.SubFactory(GeographicalAreaFactory)


class GeographicalAreaDescriptionFactory(TrackedModelMixin, ValidityStartFactoryMixin):
    class Meta:
        model = "geo_areas.GeographicalAreaDescription"

    sid = numeric_sid()
    described_geographicalarea = factory.SubFactory(
        GeographicalAreaFactory,
        description=None,
    )
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

    description = factory.RelatedFactory(
        "common.tests.factories.CertificateDescriptionFactory",
        factory_related_name="described_certificate",
        transaction=factory.SelfAttribute("..transaction"),
        validity_start=factory.SelfAttribute("..valid_between.lower"),
    )


class CertificateDescriptionFactory(TrackedModelMixin, ValidityStartFactoryMixin):
    class Meta:
        model = "certificates.CertificateDescription"

    sid = numeric_sid()

    described_certificate = factory.SubFactory(
        CertificateFactory,
        description=None,
    )
    description = short_description()


class TestModel1Factory(TrackedModelMixin, ValidityFactoryMixin):
    __test__ = False

    class Meta:
        model = TestModel1

    name = factory.Faker("text", max_nb_chars=24)
    sid = numeric_sid()


class TestModelDescription1Factory(TrackedModelMixin, ValidityStartFactoryMixin):
    class Meta:
        model = TestModelDescription1

    described_record = factory.SubFactory(TestModel1Factory)
    description = factory.Faker("text", max_nb_chars=500)


class TestModel2Factory(TrackedModelMixin, ValidityFactoryMixin):
    __test__ = False

    class Meta:
        model = TestModel2

    description = factory.Faker("text", max_nb_chars=24)
    custom_sid = numeric_sid()


class TestModel3Factory(TrackedModelMixin, ValidityFactoryMixin):
    __test__ = False

    class Meta:
        model = TestModel3

    linked_model = factory.SubFactory(TestModel1Factory)
    sid = numeric_sid()


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


class AdditionalCodeDescriptionFactory(TrackedModelMixin, ValidityStartFactoryMixin):
    class Meta:
        model = "additional_codes.AdditionalCodeDescription"

    sid = numeric_sid()
    described_additionalcode = factory.SubFactory(AdditionalCodeFactory)
    description = short_description()


class FootnoteAssociationAdditionalCodeFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "additional_codes.FootnoteAssociationAdditionalCode"

    additional_code = factory.SubFactory(AdditionalCodeFactory)
    associated_footnote = factory.SubFactory(FootnoteFactory)


class SimpleGoodsNomenclatureFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "commodities.GoodsNomenclature"

    sid = numeric_sid()
    item_id = string_sequence(10, characters=string.digits)
    suffix = "80"
    statistical = False


class GoodsNomenclatureFactory(SimpleGoodsNomenclatureFactory):
    class Meta:
        model = "commodities.GoodsNomenclature"

    indent = factory.RelatedFactory(
        "common.tests.factories.GoodsNomenclatureIndentFactory",
        factory_related_name="indented_goods_nomenclature",
        transaction=factory.SelfAttribute("..transaction"),
        validity_start=factory.SelfAttribute("..valid_between.lower"),
    )

    description = factory.RelatedFactory(
        "common.tests.factories.GoodsNomenclatureDescriptionFactory",
        factory_related_name="described_goods_nomenclature",
        transaction=factory.SelfAttribute("..transaction"),
        validity_start=factory.SelfAttribute("..valid_between.lower"),
    )

    origin = factory.RelatedFactory(
        "common.tests.factories.GoodsNomenclatureOriginFactory",
        factory_related_name="new_goods_nomenclature",
        transaction=factory.SelfAttribute("..transaction"),
    )


SimpleGoodsNomenclatureFactory.reset_sequence(1)


class GoodsNomenclatureWithSuccessorFactory(GoodsNomenclatureFactory):
    successor = factory.RelatedFactory(
        "common.tests.factories.GoodsNomenclatureSuccessorFactory",
        factory_related_name="replaced_goods_nomenclature",
        transaction=factory.SelfAttribute("..transaction"),
    )


class SimpleGoodsNomenclatureIndentFactory(
    TrackedModelMixin,
    ValidityStartFactoryMixin,
):
    class Meta:
        model = "commodities.GoodsNomenclatureIndent"

    sid = numeric_sid()
    indented_goods_nomenclature = factory.SubFactory(SimpleGoodsNomenclatureFactory)
    indent = 0


class GoodsNomenclatureIndentFactory(SimpleGoodsNomenclatureIndentFactory):
    class Meta:
        model = "commodities.GoodsNomenclatureIndent"

    node = factory.RelatedFactory(
        "common.tests.factories.GoodsNomenclatureIndentNodeFactory",
        factory_related_name="indent",
        valid_between=factory.SelfAttribute(
            "..indented_goods_nomenclature.valid_between",
        ),
        creating_transaction=factory.SelfAttribute("..transaction"),
    )


indent_path_generator = string_generator(4)


def build_indent_path(good_indent_node):
    parent = good_indent_node.parent
    if parent is not None:
        parent.numchild += 1
        parent.save()
        return parent.path + indent_path_generator()
    return indent_path_generator()


class GoodsNomenclatureIndentNodeFactory(ValidityFactoryMixin):
    class Meta:
        model = "commodities.GoodsNomenclatureIndentNode"
        exclude = ("parent",)

    parent = None

    path = factory.LazyAttribute(build_indent_path)
    depth = factory.LazyAttribute(lambda o: len(o.path) // 4)

    indent = factory.SubFactory(SimpleGoodsNomenclatureIndentFactory)

    creating_transaction = factory.SubFactory(ApprovedTransactionFactory)


class GoodsNomenclatureDescriptionFactory(TrackedModelMixin, ValidityStartFactoryMixin):
    class Meta:
        model = "commodities.GoodsNomenclatureDescription"

    sid = numeric_sid()
    described_goods_nomenclature = factory.SubFactory(
        GoodsNomenclatureFactory,
        description=None,
    )
    description = short_description()


class GoodsNomenclatureOriginFactory(TrackedModelMixin):
    class Meta:
        model = "commodities.GoodsNomenclatureOrigin"

    new_goods_nomenclature = factory.SubFactory(SimpleGoodsNomenclatureFactory)
    derived_from_goods_nomenclature = factory.SubFactory(
        SimpleGoodsNomenclatureFactory,
        valid_between=date_ranges("big"),
    )


class GoodsNomenclatureSuccessorFactory(TrackedModelMixin):
    class Meta:
        model = "commodities.GoodsNomenclatureSuccessor"

    replaced_goods_nomenclature = factory.SubFactory(
        SimpleGoodsNomenclatureFactory,
        valid_between=date_ranges("adjacent_earlier"),
    )
    absorbed_into_goods_nomenclature = factory.SubFactory(
        SimpleGoodsNomenclatureFactory,
    )


class FootnoteAssociationGoodsNomenclatureFactory(
    TrackedModelMixin,
    ValidityFactoryMixin,
):
    class Meta:
        model = "commodities.FootnoteAssociationGoodsNomenclature"

    goods_nomenclature = factory.SubFactory(GoodsNomenclatureFactory)
    associated_footnote = factory.SubFactory(FootnoteFactory)


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


class QuotaOrderNumberFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "quotas.QuotaOrderNumber"

    sid = numeric_sid()
    order_number = string_sequence(6, characters=string.digits)
    mechanism = 0
    category = 1
    valid_between = date_ranges("normal")

    origin = factory.RelatedFactory(
        "common.tests.factories.QuotaOrderNumberOriginFactory",
        factory_related_name="order_number",
        valid_between=factory.SelfAttribute("..valid_between"),
        transaction=factory.SelfAttribute("..transaction"),
    )

    @factory.post_generation
    def required_certificates(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for certificate in extracted:
                self.required_certificates.add(certificate)


class QuotaOrderNumberOriginFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "quotas.QuotaOrderNumberOrigin"

    sid = numeric_sid()
    order_number = factory.SubFactory(
        QuotaOrderNumberFactory,
        origin=None,
    )
    geographical_area = factory.SubFactory(
        GeographicalAreaFactory,
        valid_between=factory.SelfAttribute("..valid_between"),
    )


class QuotaOrderNumberOriginExclusionFactory(TrackedModelMixin):
    class Meta:
        model = "quotas.QuotaOrderNumberOriginExclusion"

    excluded_geographical_area = factory.SubFactory(
        GeographicalAreaFactory,
        area_code=AreaCode.GROUP,
    )
    origin = factory.SubFactory(
        QuotaOrderNumberOriginFactory,
        geographical_area=factory.SelfAttribute("..excluded_geographical_area"),
    )


class QuotaDefinitionFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "quotas.QuotaDefinition"

    sid = numeric_sid()
    order_number = factory.SubFactory(QuotaOrderNumberFactory)
    volume = 0
    initial_volume = 0
    monetary_unit = factory.SubFactory(MonetaryUnitFactory)
    measurement_unit = factory.SubFactory(MeasurementUnitFactory)
    maximum_precision = 0
    quota_critical = False
    quota_critical_threshold = 80
    description = short_description()


class QuotaDefinitionWithQualifierFactory(QuotaDefinitionFactory):
    measurement_unit_qualifier = factory.SubFactory(MeasurementUnitQualifierFactory)


class QuotaAssociationFactory(TrackedModelMixin):
    class Meta:
        model = "quotas.QuotaAssociation"

    main_quota = factory.SubFactory(QuotaDefinitionFactory)
    sub_quota = factory.SubFactory(QuotaDefinitionFactory)
    sub_quota_relation_type = FuzzyChoice(["EQ", "NM"])
    coefficient = Decimal("1.00000")


class EquivalentQuotaAssociationFactory(QuotaAssociationFactory):
    coefficient = Decimal("0.50000")
    sub_quota_relation_type = "EQ"


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
    blocking_period_type = FuzzyChoice(range(1, 9))
    valid_between = date_ranges("normal")


class QuotaEventFactory(TrackedModelMixin):
    class Meta:
        model = "quotas.QuotaEvent"

    subrecord_code = FuzzyChoice(QuotaEventType.values)
    quota_definition = factory.SubFactory(QuotaDefinitionFactory)
    occurrence_timestamp = factory.LazyFunction(lambda: Dates().datetime_now)

    @factory.lazy_attribute
    def data(self):
        now = f"{Dates().now:%Y-%m-%d}"
        if self.subrecord_code == "00":
            return {
                "old.balance": "0.0",
                "new.balance": "0.0",
                "imported.amount": "0.0",
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
                "transferred.amount": "0.0",
                "target.quota.definition.sid": "1",
            }


class MeasureTypeSeriesFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "measures.MeasureTypeSeries"

    sid = string_sequence(2, characters=string.ascii_uppercase)
    measure_type_combination = FuzzyChoice(MeasureTypeCombination.values)
    description = short_description()


class DutyExpressionFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "measures.DutyExpression"

    sid = FuzzyChoice(DutyExpressionId.values)
    duty_amount_applicability_code = ApplicabilityCode.PERMITTED
    measurement_unit_applicability_code = ApplicabilityCode.PERMITTED
    monetary_unit_applicability_code = ApplicabilityCode.PERMITTED
    description = short_description()


class MeasureTypeFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "measures.MeasureType"

    sid = string_sequence(3, characters=string.digits)
    trade_movement_code = FuzzyChoice(ImportExportCode.values)
    priority_code = FuzzyChoice(range(1, 10))
    measure_component_applicability_code = FuzzyChoice(ApplicabilityCode.values)
    origin_destination_code = FuzzyChoice(ImportExportCode.values)
    order_number_capture_code = OrderNumberCaptureCode.NOT_PERMITTED
    measure_explosion_level = 2
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

    code = factory.Sequence(lambda x: f"{x + 1:02d}")
    description = short_description()


class MeasureFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "measures.Measure"

    sid = numeric_sid()
    geographical_area = factory.SubFactory(GeographicalAreaFactory)
    goods_nomenclature = factory.SubFactory(GoodsNomenclatureFactory)
    measure_type = factory.SubFactory(MeasureTypeFactory)
    additional_code = None
    order_number = None
    reduction = factory.Sequence(lambda x: x % 4 + 1)
    generating_regulation = factory.SubFactory(RegulationFactory)
    stopped = False
    export_refund_nomenclature_sid = None

    @factory.lazy_attribute
    def terminating_regulation(self):
        if self.valid_between.upper is None:
            return None
        return self.generating_regulation

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        leave_measure = kwargs.pop("leave_measure", False)
        if "measure_type" in kwargs and not leave_measure:
            kwargs["measure_type"] = cls.measure_type_explosion(
                kwargs["measure_type"],
                kwargs.get("goods_nomenclature"),
            )
        obj = model_class(*args, **kwargs)
        obj.save()
        return obj

    @staticmethod
    def measure_type_explosion(measure_type, goods_nomenclature):
        if not goods_nomenclature:
            return measure_type
        item_id = goods_nomenclature.item_id
        explosion_level = 10
        while item_id.endswith("00"):
            explosion_level -= 2
            item_id = item_id[:-2]

        measure_type.measure_explosion_level = explosion_level
        measure_type.save(force_write=True)
        return measure_type


class MeasureWithAdditionalCodeFactory(MeasureFactory):
    additional_code = factory.SubFactory(AdditionalCodeFactory)


class MeasureWithQuotaFactory(MeasureFactory):
    measure_type = factory.SubFactory(
        MeasureTypeFactory,
        order_number_capture_code=OrderNumberCaptureCode.MANDATORY,
    )
    order_number = factory.SubFactory(
        QuotaOrderNumberFactory,
        origin__geographical_area=factory.SelfAttribute("...geographical_area"),
        valid_between=factory.SelfAttribute("..valid_between"),
        transaction=factory.SelfAttribute("..transaction"),
    )


class MeasureComponentFactory(TrackedModelMixin):
    class Meta:
        model = "measures.MeasureComponent"

    component_measure = factory.SubFactory(MeasureFactory)
    duty_expression = factory.SubFactory(DutyExpressionFactory)
    duty_amount = None
    monetary_unit = None
    component_measurement = None


class MeasureComponentWithMonetaryUnitFactory(MeasureComponentFactory):
    monetary_unit = factory.SubFactory(MonetaryUnitFactory)


class MeasureComponentWithMeasurementFactory(MeasureComponentFactory):
    component_measurement = factory.SubFactory(MeasurementFactory)


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


class MeasureConditionWithCertificateFactory(MeasureConditionFactory):
    required_certificate = factory.SubFactory(CertificateFactory)


class MeasureConditionWithMeasurementFactory(MeasureConditionFactory):
    condition_measurement = factory.SubFactory(MeasurementFactory)


class MeasureConditionComponentFactory(TrackedModelMixin):
    class Meta:
        model = "measures.MeasureConditionComponent"

    condition = factory.SubFactory(MeasureConditionFactory)
    duty_expression = factory.SubFactory(DutyExpressionFactory)
    duty_amount = factory.Faker("pydecimal", left_digits=7, right_digits=3)
    monetary_unit = factory.SubFactory(MonetaryUnitFactory)
    component_measurement = None


class MeasureConditionComponentWithMeasurementFactory(MeasureConditionComponentFactory):
    component_measurement = factory.SubFactory(MeasurementFactory)


class MeasureExcludedGeographicalAreaFactory(TrackedModelMixin):
    class Meta:
        model = "measures.MeasureExcludedGeographicalArea"

    modified_measure = factory.SubFactory(
        MeasureFactory,
        geographical_area__area_code=1,
    )
    excluded_geographical_area = factory.SubFactory(
        GeographicalAreaFactory,
        area_code=0,
    )


class MeasureExcludedGeographicalMembershipFactory(
    MeasureExcludedGeographicalAreaFactory,
):
    class Meta:
        exclude = ["membership"]

    membership = factory.SubFactory(
        GeographicalMembershipFactory,
        geo_group=factory.SelfAttribute("..modified_measure.geographical_area"),
        member=factory.SelfAttribute("..excluded_geographical_area"),
    )


class FootnoteAssociationMeasureFactory(TrackedModelMixin):
    class Meta:
        model = "measures.FootnoteAssociationMeasure"

    footnoted_measure = factory.SubFactory(MeasureFactory)
    associated_footnote = factory.SubFactory(FootnoteFactory)


class EnvelopeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "taric.Envelope"

    envelope_id = factory.Sequence(lambda x: f"{Dates().now:%y}{(x + 1):04d}")


class EnvelopeTransactionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "taric.EnvelopeTransaction"

    index = factory.Sequence(lambda x: x + 1)
    transaction = factory.SubFactory(TransactionFactory)
    envelope = factory.SubFactory(EnvelopeFactory)


class UploadFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "exporter.Upload"

    envelope = factory.SubFactory(EnvelopeFactory)
    correlation_id = factory.Faker("uuid4")
    checksum = factory.Faker("md5")


class ImportBatchFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "importer.ImportBatch"

    name = factory.sequence(str)


class ImporterXMLChunkFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "importer.ImporterXMLChunk"

    batch = factory.SubFactory(ImportBatchFactory)
    chunk_number = 1
    status = ImporterChunkStatus.WAITING
    chunk_text = """\
<?xml version="1.0" encoding="UTF-8"?>
<env:envelope xmlns="urn:publicid:-:DGTAXUD:TARIC:MESSAGE:1.0" xmlns:env="urn:publicid:-:DGTAXUD:GENERAL:ENVELOPE:1.0" id="1">
</env:envelope>"""


class BatchDependenciesFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "importer.BatchDependencies"

    dependent_batch = factory.SubFactory(ImportBatchFactory)
    depends_on = factory.SubFactory(ImportBatchFactory)
