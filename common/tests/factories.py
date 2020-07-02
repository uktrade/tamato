"""Factory classes for BDD tests."""
import random
import string
from datetime import datetime
from datetime import timezone
from functools import partial
from itertools import product

import factory
from psycopg2.extras import DateTimeTZRange

from common.tests.models import TestModel1
from common.tests.models import TestModel2

BREXIT_DATE = datetime(2021, 1, 1).replace(tzinfo=timezone.utc)

alphanumeric_id_generator = partial(product, string.ascii_uppercase + string.digits)


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


class FootnoteTypeDescriptionFactory(TrackedModelMixin):
    class Meta:
        model = "footnotes.FootnoteTypeDescription"

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


class RegulationFactory(TrackedModelMixin):
    class Meta:
        model = "regulations.Regulation"

    regulation_id = factory.Sequence(lambda n: f"R{datetime.now():%y}{n:04d}0")
    approved = True


area_id_product_generator = alphanumeric_id_generator(repeat=4)


class GeographicalAreaFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "geo_areas.GeographicalArea"

    sid = factory.Sequence(lambda n: n)

    area_id = factory.Sequence(lambda _: "".join(next(area_id_product_generator)))
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

    sid = factory.Sequence(lambda n: "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"[n])
    description = factory.Faker("text", max_nb_chars=500)


certificate_sid_product_generator = alphanumeric_id_generator(repeat=3)


class CertificateFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "certificates.Certificate"

    certificate_type = factory.SubFactory(CertificateTypeFactory)
    sid = factory.Sequence(lambda _: "".join(next(certificate_sid_product_generator)))


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


alphanumerics = list(string.ascii_uppercase + string.digits)


def alphanumeric_strings(length=1):
    g = product(alphanumerics, repeat=length)
    return lambda n: "".join(next(g))


class AdditionalCodeTypeFactory(TrackedModelMixin, ValidityFactoryMixin):
    """AdditionalCodeType factory."""

    class Meta:
        model = "additional_codes.AdditionalCodeType"

    sid = factory.Sequence(alphanumeric_strings(length=1))
    description = factory.Faker("text", max_nb_chars=500)
    application_code = 1


class AdditionalCodeFactory(TrackedModelMixin, ValidityFactoryMixin):
    """AdditionalCode factory."""

    class Meta:
        model = "additional_codes.AdditionalCode"

    sid = factory.Sequence(lambda n: 1 + n)
    type = factory.SubFactory(AdditionalCodeTypeFactory)
    code = factory.Sequence(alphanumeric_strings(length=3))


class AdditionalCodeDescriptionFactory(TrackedModelMixin, ValidityFactoryMixin):
    class Meta:
        model = "additional_codes.AdditionalCodeDescription"

    description_period_sid = factory.Sequence(lambda n: 1 + n)
    described_additional_code = factory.SubFactory(AdditionalCodeFactory)
    description = factory.Faker("text", max_nb_chars=500)
