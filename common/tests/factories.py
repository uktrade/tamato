"""Factory classes for BDD tests."""

import string
from decimal import Decimal
from itertools import cycle
from itertools import product

import factory
from django.contrib.auth import get_user_model
from factory.fuzzy import FuzzyChoice
from factory.fuzzy import FuzzyText
from faker import Faker

from common.models import TrackedModel
from common.models.transactions import TransactionPartition
from common.tests.models import TestModel1
from common.tests.models import TestModel2
from common.tests.models import TestModel3
from common.tests.models import TestModelDescription1
from common.tests.util import Dates
from common.tests.util import wrap_numbers_over_max_digits
from common.validators import ApplicabilityCode
from common.validators import UpdateType
from geo_areas.validators import AreaCode
from importer.models import ImportBatchStatus
from importer.models import ImporterChunkStatus
from measures.validators import DutyExpressionId
from measures.validators import ImportExportCode
from measures.validators import MeasureTypeCombination
from measures.validators import OrderNumberCaptureCode
from publishing.models import ProcessingState
from quotas.validators import QuotaEventType
from tasks.models import TaskAssignee
from tasks.models import TaskProgressState
from workbaskets.validators import WorkflowStatus

User = get_user_model()


def short_description():
    return factory.Faker("text", max_nb_chars=500)


def string_generator(length=1, characters=string.ascii_uppercase + string.digits):
    g = cycle(product(characters, repeat=length))
    return lambda *_: "".join(next(g))[::-1]


def string_sequence(length=1, characters=string.ascii_uppercase + string.digits):
    return factory.Sequence(string_generator(length, characters))


def numeric_sid():
    return factory.Sequence(lambda x: x + 1)


def duty_amount():
    return factory.LazyFunction(
        lambda: Faker().pydecimal(left_digits=7, right_digits=3, positive=True),
    )


def date_ranges(name):
    return factory.LazyFunction(lambda: getattr(Dates(), name))


def end_date(name):
    return factory.LazyFunction(lambda: getattr(Dates(), name).upper)


def factory_relation(relation_type, transaction_order, model, **kwargs):
    return relation_type(
        model,
        transaction__order=factory.LazyAttribute(
            lambda o: o.factory_parent.factory_parent.transaction.order
            + transaction_order,
        ),
        transaction__partition=factory.LazyAttribute(
            lambda o: o.factory_parent.factory_parent.transaction.partition,
        ),
        transaction__workbasket=factory.LazyAttribute(
            lambda o: o.factory_parent.factory_parent.transaction.workbasket,
        ),
        **kwargs,
    )


def subfactory(model, **kwargs):
    """Any reference to another TrackedModel needs to be created in a
    transaction previous to this one."""

    return factory_relation(factory.SubFactory, -1, model, **kwargs)


def related_factory(model, **kwargs):
    return factory_relation(factory.RelatedFactory, +1, model, **kwargs)


class ValidityFactoryMixin(factory.django.DjangoModelFactory):
    valid_between = date_ranges("no_end")


class ValidityStartFactoryMixin(factory.django.DjangoModelFactory):
    validity_start = date_ranges("now")


class UserFactory(factory.django.DjangoModelFactory):
    """User factory."""

    class Meta:
        model = User

    username = factory.sequence(lambda n: f"{factory.Faker('name')}{n}")
    email = factory.Faker("email")


class UserGroupFactory(factory.django.DjangoModelFactory):
    """User Group factory."""

    class Meta:
        model = "auth.Group"

    name = factory.Faker("bs")


class WorkBasketFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "workbaskets.WorkBasket"

    author = factory.SubFactory(UserFactory)
    title = factory.Faker("sentence", nb_words=4)


class EditingWorkBasketFactory(WorkBasketFactory):
    class Meta:
        model = "workbaskets.WorkBasket"

    status = WorkflowStatus.EDITING
    transaction = factory.RelatedFactory(
        "common.tests.factories.UnapprovedTransactionFactory",
        factory_related_name="workbasket",
    )


class ErroredWorkBasketFactory(WorkBasketFactory):
    class Meta:
        model = "workbaskets.WorkBasket"

    status = WorkflowStatus.ERRORED
    transaction = factory.RelatedFactory(
        "common.tests.factories.UnapprovedTransactionFactory",
        factory_related_name="workbasket",
    )


class QueuedWorkBasketFactory(WorkBasketFactory):
    class Meta:
        model = "workbaskets.WorkBasket"

    approver = factory.SubFactory(UserFactory)
    status = WorkflowStatus.QUEUED
    transaction = factory.RelatedFactory(
        "common.tests.factories.ApprovedTransactionFactory",
        factory_related_name="workbasket",
    )


class PublishedWorkBasketFactory(WorkBasketFactory):
    class Meta:
        model = "workbaskets.WorkBasket"

    approver = factory.SubFactory(UserFactory)
    status = WorkflowStatus.PUBLISHED
    transaction = factory.RelatedFactory(
        "common.tests.factories.ApprovedTransactionFactory",
        factory_related_name="workbasket",
    )


class SimplePublishedWorkBasketFactory(WorkBasketFactory):
    """SimplePublishedWorkBasketFactory is distinguished from
    PublishedWorkBasketFactory by having no transactions, allowing Transaction
    factories to add to the created workbasket without surplus, incidental
    transactions."""

    class Meta:
        model = "workbaskets.WorkBasket"

    approver = factory.SubFactory(UserFactory)
    status = WorkflowStatus.PUBLISHED


class SimpleQueuedWorkBasketFactory(WorkBasketFactory):
    class Meta:
        model = "workbaskets.WorkBasket"

    approver = factory.SubFactory(UserFactory)
    status = WorkflowStatus.QUEUED


class ArchivedWorkBasketFactory(WorkBasketFactory):
    class Meta:
        model = "workbaskets.WorkBasket"

    status = WorkflowStatus.ARCHIVED


class TransactionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "common.Transaction"

    order = factory.Sequence(lambda x: x + 10)
    import_transaction_id = factory.Sequence(lambda x: x + 10)
    workbasket = factory.SubFactory(SimpleQueuedWorkBasketFactory)
    composite_key = factory.Sequence(str)

    class Params:
        approved = factory.Trait(
            partition=TransactionPartition.REVISION,
        )

        published = factory.Trait(
            partition=TransactionPartition.REVISION,
            workbasket=factory.SubFactory(PublishedWorkBasketFactory),
        )

        single_published = factory.Trait(
            partition=TransactionPartition.REVISION,
            workbasket=factory.SubFactory(SimplePublishedWorkBasketFactory),
        )

        seed = factory.Trait(
            partition=TransactionPartition.SEED_FILE,
        )

        draft = factory.Trait(
            partition=TransactionPartition.DRAFT,
            workbasket=factory.SubFactory(WorkBasketFactory),
        )

        archived = factory.Trait(
            partition=TransactionPartition.DRAFT,
            workbasket=factory.SubFactory(ArchivedWorkBasketFactory),
        )


class SeedFileTransactionFactory(TransactionFactory):
    seed = True


class PublishedTransactionFactory(TransactionFactory):
    single_published = True


class ApprovedTransactionFactory(TransactionFactory):
    approved = True


class UnapprovedTransactionFactory(TransactionFactory):
    draft = True


class ArchivedTransactionFactory(TransactionFactory):
    draft = True


class VersionGroupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "common.VersionGroup"


class TrackedModelMixin(factory.django.DjangoModelFactory):
    transaction = factory.SubFactory(ApprovedTransactionFactory)
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
    footnote_type = subfactory(FootnoteTypeFactory)

    description = factory.RelatedFactory(
        "common.tests.factories.FootnoteDescriptionFactory",
        factory_related_name="described_footnote",
        transaction=factory.SelfAttribute("..transaction"),
        validity_start=factory.SelfAttribute("..valid_between.lower"),
    )

    class Params:
        associated_with_measure = factory.Trait(
            footnoteassociationmeasure=related_factory(
                "common.tests.factories.FootnoteAssociationMeasureFactory",
                factory_related_name="associated_footnote",
            ),
        )
        associated_with_goods_nomenclature = factory.Trait(
            footnoteassociationgoodsnomenclature=related_factory(
                "common.tests.factories.FootnoteAssociationGoodsNomenclatureFactory",
                factory_related_name="associated_footnote",
            ),
        )
        associated_with_additional_code = factory.Trait(
            footnoteassociationadditionalcode=related_factory(
                "common.tests.factories.FootnoteAssociationAdditionalCodeFactory",
                factory_related_name="associated_footnote",
            ),
        )

    associated_with_additional_code = False
    associated_with_goods_nomenclature = False
    associated_with_measure = False


class FootnoteDescriptionFactory(TrackedModelMixin, ValidityStartFactoryMixin):
    class Meta:
        model = "footnotes.FootnoteDescription"

    description = short_description()
    described_footnote = subfactory(
        FootnoteFactory,
        description=None,
        transaction=factory.SelfAttribute("..transaction"),
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

    regulation_id = factory.Sequence(lambda n: f"R{Dates().now:%y}{n+1:04d}0")
    approved = True
    role_type = 1
    community_code = 1
    regulation_group = subfactory(RegulationGroupFactory)
    information_text = string_sequence(length=50)
    public_identifier = factory.sequence(lambda n: f"S.I. 2021/{n}")
    url = factory.sequence(lambda n: f"https://legislation.gov.uk/uksi/2021/{n}")


class BaseRegulationFactory(RegulationFactory):
    role_type = 1
    valid_between = date_ranges("no_end")


class ModificationRegulationFactory(RegulationFactory):
    role_type = 4
    valid_between = date_ranges("no_end")

    amendment = factory.RelatedFactory(
        "common.tests.factories.AmendmentFactory",
        transaction=factory.SelfAttribute("..transaction"),
        factory_related_name="enacting_regulation",
    )


class ModifiedBaseRegulationFactory(BaseRegulationFactory):
    amendment = factory.RelatedFactory(
        "common.tests.factories.AmendmentFactory",
        transaction=factory.SelfAttribute("..transaction"),
        factory_related_name="target_regulation",
    )


class UIRegulationFactory(BaseRegulationFactory):
    """
    Regulation factory used by our UI form tests.

    These are distinct from our other Regulation factories because the required
    status differs between Regulation model fields and form fields.
    """

    published_at = date_ranges("now")


class UIDraftRegulationFactory(UIRegulationFactory):
    """Draft regulation factory used by our UI form tests."""

    regulation_id = factory.Sequence(lambda n: f"C{Dates().now:%y}{n+1:04d}0")
    approved = False


class AmendmentFactory(TrackedModelMixin):
    class Meta:
        model = "regulations.Amendment"

    target_regulation = subfactory(BaseRegulationFactory)
    enacting_regulation = factory.SubFactory(
        ModificationRegulationFactory,
        amendment=None,
        # FIXME synthetic-record-order make this field transaction=factory.SelfAttribute("..transaction")
    )


class ExtensionFactory(TrackedModelMixin):
    class Meta:
        model = "regulations.Extension"

    target_regulation = subfactory(RegulationFactory)
    enacting_regulation = factory.SubFactory(
        RegulationFactory,
        # FIXME synthetic-record-order make this field transaction=factory.SelfAttribute("..transaction")
    )


class SuspensionFactory(TrackedModelMixin):
    class Meta:
        model = "regulations.Suspension"

    target_regulation = subfactory(RegulationFactory)
    enacting_regulation = factory.SubFactory(
        RegulationFactory,
        # FIXME synthetic-record-order make this field transaction=factory.SelfAttribute("..transaction")
    )


class TerminationFactory(TrackedModelMixin):
    class Meta:
        model = "regulations.Termination"

    target_regulation = subfactory(RegulationFactory)
    enacting_regulation = factory.SubFactory(
        RegulationFactory,
        # FIXME synthetic-record-order make this field transaction=factory.SelfAttribute("..transaction")
    )

    effective_date = Dates().datetime_now


class ReplacementFactory(TrackedModelMixin):
    class Meta:
        model = "regulations.Replacement"

    target_regulation = subfactory(RegulationFactory)
    enacting_regulation = factory.SubFactory(
        RegulationFactory,
        # FIXME synthetic-record-order make this field transaction=factory.SelfAttribute("..transaction")
    )
    measure_type_id = "123456"
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

    class Params:
        has_parent = factory.Trait(
            parent=subfactory("common.tests.factories.GeoGroupFactory"),
        )

    has_parent = False


class RegionFactory(GeographicalAreaFactory):
    area_code = 2


class GeographicalMembershipFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "geo_areas.GeographicalMembership"

    geo_group = subfactory(GeoGroupFactory)
    member = factory.SubFactory(
        GeographicalAreaFactory,
        # FIXME synthetic-record-order make this field transaction=factory.SelfAttribute("..transaction")
    )


class GeographicalAreaDescriptionFactory(TrackedModelMixin, ValidityStartFactoryMixin):
    class Meta:
        model = "geo_areas.GeographicalAreaDescription"

    sid = numeric_sid()
    described_geographicalarea = subfactory(
        GeographicalAreaFactory,
        description=None,
        transaction=factory.SelfAttribute("..transaction"),
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

    certificate_type = subfactory(CertificateTypeFactory)
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

    described_certificate = subfactory(
        CertificateFactory,
        description=None,
        transaction=factory.SelfAttribute("..transaction"),
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

    described_record = subfactory(
        TestModel1Factory,
        transaction=factory.SelfAttribute("..transaction"),
    )
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

    linked_model = subfactory(TestModel1Factory)
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
    type = subfactory(AdditionalCodeTypeFactory)
    code = string_sequence(3)


class AdditionalCodeDescriptionFactory(TrackedModelMixin, ValidityStartFactoryMixin):
    class Meta:
        model = "additional_codes.AdditionalCodeDescription"

    sid = numeric_sid()
    described_additionalcode = subfactory(
        AdditionalCodeFactory,
        transaction=factory.SelfAttribute("..transaction"),
    )
    description = short_description()


class FootnoteAssociationAdditionalCodeFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "additional_codes.FootnoteAssociationAdditionalCode"

    additional_code = subfactory(AdditionalCodeFactory)
    associated_footnote = subfactory(FootnoteFactory)


class SimpleGoodsNomenclatureFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "commodities.GoodsNomenclature"

    sid = numeric_sid()
    item_id = string_sequence(10, characters=string.digits)
    suffix = "80"
    statistical = False


class GoodsNomenclatureFactory(SimpleGoodsNomenclatureFactory):
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
        transaction=factory.SelfAttribute("..transaction"),
        factory_related_name="new_goods_nomenclature",
    )

    version_group = factory.SubFactory(VersionGroupFactory)


SimpleGoodsNomenclatureFactory.reset_sequence(1)


class GoodsNomenclatureWithSuccessorFactory(GoodsNomenclatureFactory):
    successor = factory.RelatedFactory(
        "common.tests.factories.GoodsNomenclatureSuccessorFactory",
        transaction=factory.SelfAttribute("..transaction"),
        factory_related_name="replaced_goods_nomenclature",
    )


class SimpleGoodsNomenclatureIndentFactory(
    TrackedModelMixin,
    ValidityStartFactoryMixin,
):
    class Meta:
        model = "commodities.GoodsNomenclatureIndent"

    sid = numeric_sid()
    indented_goods_nomenclature = subfactory(SimpleGoodsNomenclatureFactory)
    indent = 0


class GoodsNomenclatureIndentFactory(SimpleGoodsNomenclatureIndentFactory):
    class Meta:
        model = "commodities.GoodsNomenclatureIndent"


class GoodsNomenclatureDescriptionFactory(TrackedModelMixin, ValidityStartFactoryMixin):
    class Meta:
        model = "commodities.GoodsNomenclatureDescription"

    sid = numeric_sid()
    described_goods_nomenclature = subfactory(
        GoodsNomenclatureFactory,
        description=None,
        transaction=factory.SelfAttribute("..transaction"),
    )
    description = short_description()


class GoodsNomenclatureOriginFactory(TrackedModelMixin):
    class Meta:
        model = "commodities.GoodsNomenclatureOrigin"

    new_goods_nomenclature = subfactory(SimpleGoodsNomenclatureFactory)
    derived_from_goods_nomenclature = subfactory(
        SimpleGoodsNomenclatureFactory,
        valid_between=date_ranges("big"),
    )


class GoodsNomenclatureSuccessorFactory(TrackedModelMixin):
    class Meta:
        model = "commodities.GoodsNomenclatureSuccessor"

    replaced_goods_nomenclature = subfactory(
        SimpleGoodsNomenclatureFactory,
        valid_between=date_ranges("adjacent_earlier"),
    )
    absorbed_into_goods_nomenclature = subfactory(SimpleGoodsNomenclatureFactory)


class FootnoteAssociationGoodsNomenclatureFactory(
    TrackedModelMixin,
    ValidityFactoryMixin,
):
    class Meta:
        model = "commodities.FootnoteAssociationGoodsNomenclature"

    goods_nomenclature = subfactory(GoodsNomenclatureFactory)
    associated_footnote = subfactory(FootnoteFactory)


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

    measurement_unit = subfactory(MeasurementUnitFactory)
    measurement_unit_qualifier = subfactory(MeasurementUnitQualifierFactory)


class MonetaryUnitFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "measures.MonetaryUnit"

    code = string_sequence(3, characters=string.ascii_uppercase)
    description = short_description()


class QuotaOrderNumberFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "quotas.QuotaOrderNumber"

    sid = numeric_sid()
    order_number = FuzzyText(length=4, chars=string.digits, prefix="05")
    mechanism = 0
    category = 1
    valid_between = date_ranges("big_no_end")

    origin = factory.RelatedFactory(
        "common.tests.factories.QuotaOrderNumberOriginFactory",
        factory_related_name="order_number",
        transaction=factory.SelfAttribute("..transaction"),
        valid_between=factory.SelfAttribute("..valid_between"),
    )

    @factory.post_generation
    def required_certificates(self, create, extracted, **kwargs):
        if not create:
            return

        # Specifically checks for None so that empty arrays don't create
        if extracted is None and not any(kwargs):
            return

        # If the user just passed kwargs or just said
        # `required_certificates=True` then create a single certificate.
        if extracted is None or extracted is True:
            extracted = [
                CertificateFactory.create(
                    **{
                        "valid_between": self.valid_between,
                        "transaction": self.transaction,
                        **kwargs,
                    },
                ),
            ]
        else:
            # Else set any kwargs on the passed certificates.
            for cert in extracted:
                for field in kwargs:
                    setattr(cert, field, kwargs[field])
                cert.save(force_write=True)

        for cert in extracted:
            self.required_certificates.add(cert)


class QuotaOrderNumberOriginFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "quotas.QuotaOrderNumberOrigin"

    sid = numeric_sid()
    order_number = subfactory(
        QuotaOrderNumberFactory,
        origin=None,
    )
    geographical_area = subfactory(
        GeographicalAreaFactory,
        valid_between=factory.SelfAttribute("..valid_between"),
    )


class QuotaOrderNumberOriginExclusionFactory(TrackedModelMixin):
    class Meta:
        model = "quotas.QuotaOrderNumberOriginExclusion"

    excluded_geographical_area = subfactory(
        GeographicalAreaFactory,
        area_code=AreaCode.GROUP,
    )
    origin = subfactory(
        QuotaOrderNumberOriginFactory,
        geographical_area=factory.SelfAttribute("..excluded_geographical_area"),
    )


class QuotaDefinitionFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "quotas.QuotaDefinition"

    sid = numeric_sid()
    order_number = subfactory(
        QuotaOrderNumberFactory,
        valid_between=factory.SelfAttribute("..valid_between"),
    )
    volume = Decimal("0.000")
    initial_volume = Decimal("0.000")
    monetary_unit = None
    measurement_unit = None
    measurement_unit_qualifier = None
    maximum_precision = 0
    quota_critical = False
    quota_critical_threshold = 80
    description = short_description()

    class Params:
        is_monetary = factory.Trait(
            monetary_unit=subfactory(MonetaryUnitFactory),
        )
        is_physical = factory.Trait(
            measurement_unit=subfactory(MeasurementUnitFactory),
        )
        has_qualifier = factory.Trait(
            measurement_unit_qualifier=subfactory(MeasurementUnitQualifierFactory),
        )

    is_monetary = False
    is_physical = True
    has_qualifier = False


class QuotaDefinitionWithQualifierFactory(QuotaDefinitionFactory):
    has_qualifier = True


class QuotaAssociationFactory(TrackedModelMixin):
    class Meta:
        model = "quotas.QuotaAssociation"

    main_quota = subfactory(
        QuotaDefinitionFactory,
    )
    sub_quota = subfactory(
        QuotaDefinitionFactory,
    )
    sub_quota_relation_type = FuzzyChoice(["EQ", "NM"])
    coefficient = Decimal("1.00000")


class EquivalentQuotaAssociationFactory(QuotaAssociationFactory):
    coefficient = Decimal("0.50000")
    sub_quota_relation_type = "EQ"


class QuotaSuspensionFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "quotas.QuotaSuspension"

    sid = numeric_sid()
    quota_definition = subfactory(
        QuotaDefinitionFactory,
    )
    description = short_description()
    valid_between = date_ranges("normal")


class QuotaBlockingFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "quotas.QuotaBlocking"

    sid = numeric_sid()
    quota_definition = subfactory(
        QuotaDefinitionFactory,
    )
    blocking_period_type = FuzzyChoice(range(1, 9))
    valid_between = date_ranges("normal")


class QuotaEventFactory(TrackedModelMixin):
    class Meta:
        model = "quotas.QuotaEvent"

    subrecord_code = FuzzyChoice(QuotaEventType.values)
    quota_definition = subfactory(
        QuotaDefinitionFactory,
    )
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
    measure_type_series = subfactory(MeasureTypeSeriesFactory)


class AdditionalCodeTypeMeasureTypeFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "measures.AdditionalCodeTypeMeasureType"

    measure_type = subfactory(MeasureTypeFactory)
    additional_code_type = subfactory(AdditionalCodeTypeFactory)


class MeasureConditionCodeFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "measures.MeasureConditionCode"

    code = string_sequence(2, characters=string.ascii_uppercase)
    description = short_description()


class MeasureActionFactory(TrackedModelMixin, ValidityFactoryMixin):
    """
    MeasureActions in the TaMaTo are essentially fixed, it would be more
    realistic to test using a fixed list, however it is convenient.

    As MeasureActionFactory is used in tests, it is possible to generate more
    than 999 MeasureActions, to avoid creating MeasureAction codes with four
    digits, which is not allowed, the code wraps back to 000 every 1000
    iterations.
    """

    class Meta:
        model = "measures.MeasureAction"

    # Code should only contain 3 digits, modulo 1000 is used to wrap it.
    code = factory.Sequence(lambda x: f"{wrap_numbers_over_max_digits(x + 1, 3):02d}")
    description = short_description()


class MeasureActionPairFactory(factory.django.DjangoModelFactory):
    """Factory that takes two Measure Actions positive_action &
    negative_action."""

    class Meta:
        model = "measures.MeasureActionPair"


class MeasureFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "measures.Measure"

    sid = numeric_sid()
    geographical_area = subfactory(GeographicalAreaFactory)
    goods_nomenclature = subfactory(GoodsNomenclatureFactory)
    measure_type = subfactory(MeasureTypeFactory)
    additional_code = None
    order_number = None
    reduction = factory.Sequence(lambda x: x % 4 + 1)
    generating_regulation = subfactory(RegulationFactory)
    stopped = False
    export_refund_nomenclature_sid = None

    class Params:
        with_order_number = factory.Trait(
            measure_type=subfactory(
                MeasureTypeFactory,
                order_number_capture_code=OrderNumberCaptureCode.MANDATORY,
            ),
            order_number=subfactory(
                QuotaOrderNumberFactory,
                origin__geographical_area=factory.SelfAttribute("...geographical_area"),
                valid_between=factory.SelfAttribute("..valid_between"),
            ),
        )

        with_dead_order_number = factory.Trait(
            measure_type=subfactory(
                MeasureTypeFactory,
                order_number_capture_code=OrderNumberCaptureCode.MANDATORY,
            ),
            order_number=subfactory(
                QuotaOrderNumberFactory,
                origin__geographical_area=factory.SelfAttribute("...geographical_area"),
                valid_between=factory.SelfAttribute("..valid_between"),
            ),
        )

        with_dead_additional_code = factory.Trait(
            dead_additional_code="AAAA",
        )

        with_additional_code = factory.Trait(
            additional_code=subfactory(AdditionalCodeFactory),
        )

        with_footnote = factory.Trait(
            association=factory.RelatedFactory(
                "common.tests.factories.FootnoteAssociationMeasureFactory",
                transaction=factory.SelfAttribute("..transaction"),
                factory_related_name="footnoted_measure",
            ),
        )

        with_exclusion = factory.Trait(
            exclusion=factory.RelatedFactory(
                "common.tests.factories.MeasureExcludedGeographicalAreaFactory",
                transaction=factory.SelfAttribute("..transaction"),
                factory_related_name="modified_measure",
            ),
        )

        with_condition = factory.Trait(
            condition=factory.RelatedFactory(
                "common.tests.factories.MeasureConditionFactory",
                transaction=factory.SelfAttribute("..transaction"),
                factory_related_name="dependent_measure",
            ),
        )

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
            explosion_level = max(2, explosion_level - 2)
            item_id = item_id[:-2]

        measure_type.measure_explosion_level = explosion_level
        measure_type.save(force_write=True)
        return measure_type


class MeasureWithAdditionalCodeFactory(MeasureFactory):
    additional_code = subfactory(AdditionalCodeFactory)


class MeasureWithQuotaFactory(MeasureFactory):
    measure_type = subfactory(
        MeasureTypeFactory,
        order_number_capture_code=OrderNumberCaptureCode.MANDATORY,
    )
    order_number = subfactory(
        QuotaOrderNumberFactory,
        origin__geographical_area=factory.SelfAttribute("...geographical_area"),
        valid_between=factory.SelfAttribute("..valid_between"),
    )


class MeasureComponentFactory(TrackedModelMixin):
    class Meta:
        model = "measures.MeasureComponent"

    component_measure = subfactory(MeasureFactory)
    duty_expression = subfactory(DutyExpressionFactory)
    duty_amount = None
    monetary_unit = None
    component_measurement = None


class MeasureComponentWithMonetaryUnitFactory(MeasureComponentFactory):
    monetary_unit = subfactory(MonetaryUnitFactory)


class MeasureComponentWithMeasurementFactory(MeasureComponentFactory):
    component_measurement = subfactory(MeasurementFactory)


class MeasureConditionFactory(TrackedModelMixin):
    class Meta:
        model = "measures.MeasureCondition"

    sid = numeric_sid()
    dependent_measure = subfactory(MeasureFactory)
    condition_code = subfactory(MeasureConditionCodeFactory)
    component_sequence_number = factory.Faker("random_int", min=1, max=999)
    duty_amount = duty_amount()
    monetary_unit = subfactory(MonetaryUnitFactory)
    condition_measurement = None
    action = subfactory(MeasureActionFactory)
    required_certificate = None


class MeasureConditionWithCertificateFactory(MeasureConditionFactory):
    required_certificate = subfactory(CertificateFactory)


class MeasureConditionWithMeasurementFactory(MeasureConditionFactory):
    condition_measurement = subfactory(MeasurementFactory)


class MeasureConditionComponentFactory(TrackedModelMixin):
    class Meta:
        model = "measures.MeasureConditionComponent"

    condition = subfactory(MeasureConditionFactory)
    duty_expression = subfactory(DutyExpressionFactory)
    duty_amount = duty_amount()
    monetary_unit = subfactory(MonetaryUnitFactory)
    component_measurement = None


class MeasureConditionComponentWithMeasurementFactory(MeasureConditionComponentFactory):
    component_measurement = subfactory(MeasurementFactory)


class MeasureExcludedGeographicalAreaFactory(TrackedModelMixin):
    class Meta:
        model = "measures.MeasureExcludedGeographicalArea"

    modified_measure = subfactory(
        MeasureFactory,
        geographical_area__area_code=1,
    )
    excluded_geographical_area = subfactory(
        GeographicalAreaFactory,
        area_code=0,
    )


class MeasureExcludedGeographicalMembershipFactory(
    MeasureExcludedGeographicalAreaFactory,
):
    class Meta:
        exclude = ["membership"]

    membership = subfactory(
        GeographicalMembershipFactory,
        geo_group=factory.SelfAttribute("..modified_measure.geographical_area"),
        member=factory.SelfAttribute("..excluded_geographical_area"),
    )


class FootnoteAssociationMeasureFactory(TrackedModelMixin):
    class Meta:
        model = "measures.FootnoteAssociationMeasure"

    footnoted_measure = subfactory(MeasureFactory)
    associated_footnote = subfactory(FootnoteFactory)


class EnvelopeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "taric.Envelope"

    envelope_id = factory.Sequence(lambda x: f"{Dates().now:%y}{(x + 1):04d}")


class EnvelopeTransactionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "taric.EnvelopeTransaction"

    order = factory.Sequence(lambda x: x + 1)
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
    author = factory.SubFactory(UserFactory)
    status = ImportBatchStatus.IMPORTING
    split_job = False
    created_at = factory.Faker("date_object")
    workbasket = factory.SubFactory(WorkBasketFactory)


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


class NotifiedUserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "notifications.NotifiedUser"

    email = factory.Faker("email")
    enrol_packaging = True


class NotificationLogFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "notifications.NotificationLog"

    template_id = string_sequence(length=10)
    recipients = factory.Faker("text", max_nb_chars=24)


class PackagedWorkBasketFactory(factory.django.DjangoModelFactory):
    """Creates a PackagedWorkBasket instance associated with an approved
    WorkBasket."""

    class Meta:
        model = "publishing.PackagedWorkBasket"

    workbasket = factory.SubFactory(SimpleQueuedWorkBasketFactory)
    theme = string_sequence(length=50)
    jira_url = "www.fakejiraticket.com"


class QueuedPackagedWorkBasketFactory(PackagedWorkBasketFactory):
    """Creates a PackagedWorkBasket instance associated with an approved
    WorkBasket that contains transactions."""

    workbasket = factory.SubFactory(QueuedWorkBasketFactory)


class PublishedEnvelopeFactory(factory.django.DjangoModelFactory):
    """Creates an Envelope instance."""

    class Meta:
        model = "publishing.Envelope"

    packaged_work_basket = factory.SubFactory(QueuedPackagedWorkBasketFactory)


class SuccessPackagedWorkBasketFactory(PackagedWorkBasketFactory):
    """Creates a packaged workbasket instance with a published workbasket and in
    a successfully processed state."""

    workbasket = factory.SubFactory(PublishedWorkBasketFactory)
    processing_state = ProcessingState.SUCCESSFULLY_PROCESSED


class LoadingReportFactory(factory.django.DjangoModelFactory):
    """Creates a LoadingReport instance with an associated packaged
    workbasket."""

    class Meta:
        model = "publishing.LoadingReport"

    file_name = factory.Sequence(lambda n: f"REPORT_DBT2300{n}.html")
    comments = short_description()
    packaged_workbasket = factory.SubFactory(PackagedWorkBasketFactory)


class APIPublishedEnvelope(factory.django.DjangoModelFactory):
    class Meta:
        model = "publishing.Envelope"

    published_to_tariffs_api = date_ranges("now")
    packaged_work_basket = factory.SubFactory(SuccessPackagedWorkBasketFactory)


class UploadedPackagedWorkBasketFactory(PackagedWorkBasketFactory):
    envelope = factory.SubFactory(PublishedEnvelopeFactory)


class OperationalStatusFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "publishing.OperationalStatus"


class CrownDependenciesEnvelopeFactory(factory.django.DjangoModelFactory):
    """Creates a CrownDependenciesEnvelope instance with a successful packaged
    work basket instance."""

    class Meta:
        model = "publishing.CrownDependenciesEnvelope"

    packaged_work_basket = factory.SubFactory(SuccessPackagedWorkBasketFactory)


class CrownDependenciesPublishingTaskFactory(factory.django.DjangoModelFactory):
    """Creates a CrownDependenciesPublishingTask instance."""

    class Meta:
        model = "publishing.CrownDependenciesPublishingTask"


class CrownDependenciesPublishingOperationalStatusFactory(
    factory.django.DjangoModelFactory,
):
    """Creates a CrownDependenciesPublishingOperationalStatus instance."""

    class Meta:
        model = "publishing.CrownDependenciesPublishingOperationalStatus"


class DataUploadFactory(factory.django.DjangoModelFactory):
    """Creates a DataUpload instance."""

    class Meta:
        model = "workbaskets.DataUpload"

    raw_data = factory.Faker("text", max_nb_chars=500)
    workbasket = factory.SubFactory(WorkBasketFactory)


class DataRowFactory(factory.django.DjangoModelFactory):
    """Creates a DataRow instance."""

    class Meta:
        model = "workbaskets.DataRow"

    data_upload = factory.SubFactory(DataUploadFactory)
    commodity = factory.SubFactory(GoodsNomenclatureFactory)
    duty_sentence = factory.Faker("text", max_nb_chars=24)
    valid_between = date_ranges("no_end")


class SucceededImportBatchFactory(ImportBatchFactory):
    status = ImportBatchStatus.SUCCEEDED
    goods_import = True
    taric_file = "goods.xml"


class GoodsSuccessfulImportNotificationFactory(factory.django.DjangoModelFactory):
    """This is a factory for a goods report notification, requires an import id
    passed by notified_object_id."""

    class Meta:
        model = "notifications.GoodsSuccessfulImportNotification"


class EnvelopeReadyForProcessingNotificationFactory(factory.django.DjangoModelFactory):
    """This is a factory for an envelope ready for processing notificaiton."""

    class Meta:
        model = "notifications.EnvelopeReadyForProcessingNotification"


class EnvelopeAcceptedNotificationFactory(factory.django.DjangoModelFactory):
    """This is a factory for an envelope that has been accepted notification."""

    class Meta:
        model = "notifications.EnvelopeAcceptedNotification"


class EnvelopeRejectedNotificationFactory(factory.django.DjangoModelFactory):
    """This is a factory for an envelope that has been rejected notification."""

    class Meta:
        model = "notifications.EnvelopeRejectedNotification"


class CrownDependenciesEnvelopeSuccessNotificationFactory(
    factory.django.DjangoModelFactory,
):
    """This is a factory for a crown dependencies envelope success
    notification."""

    class Meta:
        model = "notifications.CrownDependenciesEnvelopeSuccessNotification"


class CrownDependenciesEnvelopeFailedNotificationFactory(
    factory.django.DjangoModelFactory,
):
    """This is a factory for a crown dependencies envelope failed
    notification."""

    class Meta:
        model = "notifications.CrownDependenciesEnvelopeFailedNotification"


class TaskCategoryFactory(factory.django.DjangoModelFactory):
    name = factory.Faker("word")

    class Meta:
        model = "tasks.TaskCategory"


class TaskProgressStateFactory(factory.django.DjangoModelFactory):
    name = FuzzyChoice(TaskProgressState.State.values)

    class Meta:
        model = "tasks.TaskProgressState"
        django_get_or_create = ("name",)


class TaskFactory(factory.django.DjangoModelFactory):
    title = factory.Faker("sentence")
    description = factory.Faker("sentence")
    category = factory.SubFactory(TaskCategoryFactory)
    progress_state = factory.SubFactory(TaskProgressStateFactory)
    workbasket = factory.SubFactory(WorkBasketFactory)
    creator = factory.SubFactory(UserFactory)

    class Meta:
        model = "tasks.Task"


class SubTaskFactory(TaskFactory):
    parent_task = factory.SubFactory(TaskFactory)


class TaskAssigneeFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    assignment_type = FuzzyChoice(TaskAssignee.AssignmentType.values)
    task = factory.SubFactory(TaskFactory)

    class Meta:
        model = "tasks.TaskAssignee"


class AssignedWorkBasketFactory(WorkBasketFactory):
    """Creates a workbasket which has an assigned worker and reviewer."""

    @factory.post_generation
    def create_workbasket_assignments(self, create, extracted, **kwargs):
        if not create:
            return

        task = TaskFactory.create(workbasket=self)
        TaskAssigneeFactory.create(
            assignment_type=TaskAssignee.AssignmentType.WORKBASKET_WORKER,
            task=task,
        )
        TaskAssigneeFactory.create(
            assignment_type=TaskAssignee.AssignmentType.WORKBASKET_REVIEWER,
            task=task,
        )


class CommentFactory(factory.django.DjangoModelFactory):
    author = factory.SubFactory(UserFactory)
    content = factory.Faker("sentence")
    task = factory.SubFactory(TaskFactory)

    class Meta:
        model = "tasks.Comment"
