"""Factory classes for BDD tests."""
import random
import string
from datetime import datetime
from datetime import timezone
from decimal import Decimal
from itertools import product

import factory.fuzzy
from psycopg2.extras import DateTimeTZRange

from common.tests.models import TestModel1
from common.tests.models import TestModel2
from common.validators import UpdateType

BREXIT_DATE = datetime(2021, 1, 1, tzinfo=timezone.utc)


def short_description():
    return factory.Faker("text", max_nb_chars=500)


def string_generator(length=1, characters=string.ascii_uppercase + string.digits):
    g = product(characters, repeat=length)
    return lambda *_: "".join(next(g))


def string_sequence(length=1, characters=string.ascii_uppercase + string.digits):
    return factory.Sequence(string_generator(length, characters))


def numeric_sid():
    seq = string_sequence(length=8, characters=string.digits)
    seq.function(0)  # discard 0 as SIDs start from 1
    return seq


class ValidityFactoryMixin(factory.django.DjangoModelFactory):
    valid_between = DateTimeTZRange(BREXIT_DATE, None)


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

    group_id = string_sequence(3)
    description = short_description()
    valid_between = DateTimeTZRange(BREXIT_DATE, None)


class RegulationFactory(TrackedModelMixin):
    class Meta:
        model = "regulations.Regulation"

    regulation_id = factory.Sequence(
        lambda n: f"R{datetime.now(timezone.utc):%y}{n:04d}0"
    )
    approved = True
    role_type = 1
    valid_between = factory.LazyAttribute(
        lambda o: DateTimeTZRange(BREXIT_DATE, None) if o.role_type == 1 else None
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

    sid = factory.Sequence(lambda x: x + 1)

    described_certificate = factory.SubFactory(CertificateFactory)
    description = short_description()


class TestModel1Factory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = TestModel1

    name = factory.Faker("text", max_nb_chars=24)
    sid = factory.Sequence(lambda x: x + 1)


class TestModel2Factory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = TestModel2

    description = factory.Faker("text", max_nb_chars=24)
    custom_sid = factory.Sequence(lambda x: x + 1)


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

    sid = factory.Sequence(lambda x: x + 1)
    type = factory.SubFactory(AdditionalCodeTypeFactory)
    code = string_sequence(3)


class AdditionalCodeDescriptionFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "additional_codes.AdditionalCodeDescription"

    description_period_sid = factory.Sequence(lambda x: x + 1)
    described_additional_code = factory.SubFactory(AdditionalCodeFactory)
    description = short_description()


class GoodsNomenclatureFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "commodities.GoodsNomenclature"

    sid = numeric_sid()
    item_id = string_sequence(10, characters=string.digits)
    suffix = "80"
    statistical = False


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
    indented_goods_nomenclature = factory.SubFactory(GoodsNomenclatureFactory)


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
    valid_between = DateTimeTZRange(datetime(2020, 1, 1), datetime(2021, 1, 1))


class QuotaBlockingFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "quotas.QuotaBlocking"

    sid = numeric_sid()
    quota_definition = factory.SubFactory(QuotaDefinitionFactory)
    blocking_period_type = factory.fuzzy.FuzzyChoice(range(1, 9))
    valid_between = DateTimeTZRange(datetime(2020, 1, 1), datetime(2021, 1, 1))


class QuotaEventFactory(TrackedModelMixin):
    class Meta:
        model = "quotas.QuotaEvent"

    subrecord_code = factory.fuzzy.FuzzyChoice(
        ["00", "05", "10", "15", "20", "25", "30"]
    )
    quota_definition = factory.SubFactory(QuotaDefinitionFactory)
    occurrence_timestamp = datetime.now(tz=timezone.utc)

    @factory.lazy_attribute
    def data(self):
        now = "{:%Y-%m-%d}".format(datetime.now(tz=timezone.utc))
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
