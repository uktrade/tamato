"""Factory classes for BDD tests."""
import random
import string
from datetime import datetime
from datetime import timezone
from itertools import product

import factory
from psycopg2.extras import DateTimeTZRange

from common.models import UpdateType
from common.tests.models import TestModel1
from common.tests.models import TestModel2

BREXIT_DATE = datetime(2021, 1, 1).replace(tzinfo=timezone.utc)


def string_generator(length=1, characters=string.ascii_uppercase + string.digits):
    g = product(characters, repeat=length)
    return lambda *_: "".join(next(g))


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
    update_type = UpdateType.Insert.value


class FootnoteTypeFactory(TrackedModelMixin, ValidityFactoryMixin):
    """FootnoteType factory."""

    class Meta:
        model = "footnotes.FootnoteType"

    footnote_type_id = factory.Faker(
        "password",
        length=2,
        special_chars=False,
        digits=False,
        upper_case=True,
        lower_case=False,
    )
    application_code = 2
    description = factory.Faker("text", max_nb_chars=500)


class FootnoteFactory(TrackedModelMixin, ValidityFactoryMixin):
    """Footnote factory."""

    class Meta:
        model = "footnotes.Footnote"

    footnote_id = factory.Sequence(lambda n: f"{n:03d}")
    footnote_type = factory.SubFactory(FootnoteTypeFactory)


class FootnoteDescriptionFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "footnotes.FootnoteDescription"

    description = factory.Faker("text", max_nb_chars=500)
    described_footnote = factory.SubFactory(FootnoteFactory)
    description_period_sid = factory.Sequence(lambda n: 1 + n)


regulation_group_id_generator = product(string.ascii_uppercase, repeat=3)


class RegulationGroupFactory(TrackedModelMixin):
    class Meta:
        model = "regulations.Group"

    group_id = factory.Sequence(string_generator(3))
    description = factory.Faker("text", max_nb_chars=500)
    valid_between = DateTimeTZRange(BREXIT_DATE, None)


class RegulationFactory(TrackedModelMixin):
    class Meta:
        model = "regulations.Regulation"

    regulation_id = factory.Sequence(lambda n: f"R{datetime.now():%y}{n:04d}0")
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

    sid = factory.Sequence(lambda n: n + 1)

    area_id = factory.Sequence(string_generator(4))
    area_code = factory.LazyFunction(lambda: random.randint(0, 2))


class GeographicalMembershipFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "geo_areas.GeographicalMembership"

    geo_group = factory.SubFactory(GeographicalAreaFactory, area_code=1)
    member = factory.SubFactory(
        GeographicalAreaFactory,
        area_code=factory.LazyFunction(lambda: random.choice([0, 2])),
    )


class GeographicalAreaDescriptionFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "geo_areas.GeographicalAreaDescription"

    area = factory.SubFactory(GeographicalAreaFactory)
    description = factory.Faker("text", max_nb_chars=500)


class CertificateTypeFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "certificates.CertificateType"

    sid = factory.Sequence(string_generator(1))
    description = factory.Faker("text", max_nb_chars=500)


class CertificateFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "certificates.Certificate"

    certificate_type = factory.SubFactory(CertificateTypeFactory)
    sid = factory.Sequence(string_generator(3))


class CertificateDescriptionFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "certificates.CertificateDescription"

    sid = factory.sequence(lambda n: n)

    described_certificate = factory.SubFactory(CertificateFactory)
    description = factory.Faker("text", max_nb_chars=500)


class TestModel1Factory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = TestModel1

    name = factory.Faker("text", max_nb_chars=24)
    sid = factory.Sequence(lambda n: n)


class TestModel2Factory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = TestModel2

    description = factory.Faker("text", max_nb_chars=24)
    custom_sid = factory.Sequence(lambda n: n)


class AdditionalCodeTypeFactory(TrackedModelMixin, ValidityFactoryMixin):
    """AdditionalCodeType factory."""

    class Meta:
        model = "additional_codes.AdditionalCodeType"

    sid = factory.Sequence(string_generator(length=1))
    description = factory.Faker("text", max_nb_chars=500)
    application_code = 1


class AdditionalCodeFactory(TrackedModelMixin, ValidityFactoryMixin):
    """AdditionalCode factory."""

    class Meta:
        model = "additional_codes.AdditionalCode"

    sid = factory.Sequence(lambda n: 1 + n)
    type = factory.SubFactory(AdditionalCodeTypeFactory)
    code = factory.Sequence(string_generator(length=3))


class AdditionalCodeDescriptionFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "additional_codes.AdditionalCodeDescription"

    description_period_sid = factory.Sequence(lambda n: 1 + n)
    described_additional_code = factory.SubFactory(AdditionalCodeFactory)
    description = factory.Faker("text", max_nb_chars=500)


class GoodsNomenclatureFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "commodities.GoodsNomenclature"

    sid = factory.Sequence(lambda n: n + 1)
    item_id = factory.Sequence(string_generator(10, characters=string.digits))
    suffix = 80
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

    sid = factory.Sequence(lambda n: n + 1)
    indented_goods_nomenclature = factory.SubFactory(GoodsNomenclatureFactory)


class GoodsNomenclatureDescriptionFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "commodities.GoodsNomenclatureDescription"

    sid = factory.Sequence(lambda n: n + 1)
    described_goods_nomenclature = factory.SubFactory(GoodsNomenclatureFactory)
    description = factory.Faker("text", max_nb_chars=500)


class FootnoteAssociationGoodsNomenclatureFactory(
    TrackedModelMixin, ValidityFactoryMixin
):
    class Meta:
        model = "commodities.FootnoteAssociationGoodsNomenclature"

    goods_nomenclature = factory.SubFactory(GoodsNomenclatureFactory)
    associated_footnote = factory.SubFactory(FootnoteFactory)
