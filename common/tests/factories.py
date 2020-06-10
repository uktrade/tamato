"""Factory classes for BDD tests."""
import random
from datetime import datetime
from datetime import timezone

import factory
from psycopg2.extras import DateTimeTZRange


BREXIT_DATE = datetime(2021, 1, 1).replace(tzinfo=timezone.utc)


class ValidityFactoryMixin(factory.django.DjangoModelFactory):
    valid_between = DateTimeTZRange(BREXIT_DATE, None)


class FootnoteTypeFactory(ValidityFactoryMixin):
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


class FootnoteTypeDescriptionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "footnotes.FootnoteTypeDescription"

    description = factory.Faker("text", max_nb_chars=500)


class FootnoteFactory(ValidityFactoryMixin):
    """Footnote factory."""

    class Meta:
        model = "footnotes.Footnote"

    footnote_id = factory.Sequence(lambda n: f"{n:03d}")
    footnote_type = factory.SubFactory(FootnoteTypeFactory)


class FootnoteDescriptionFactory(ValidityFactoryMixin):
    class Meta:
        model = "footnotes.FootnoteDescription"

    description = factory.Faker("text", max_nb_chars=500)


class UserFactory(factory.django.DjangoModelFactory):
    """User factory."""

    class Meta:
        model = "auth.User"


class RegulationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "regulations.Regulation"

    regulation_id = factory.Sequence(lambda n: f"R{datetime.now():%y}{n:04d}0")
    approved = True


class WorkBasketFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "workbaskets.WorkBasket"


class GeographicalAreaFactory(ValidityFactoryMixin):
    class Meta:
        model = "geo_areas.GeographicalArea"

    sid = factory.Sequence(lambda n: n)
    area_id = factory.Sequence(lambda n: f"AB{n}" if n > 10 else f"ABC{n}")
    area_code = factory.LazyFunction(lambda: random.randint(0, 2))


class GeographicalMembershipFactory(ValidityFactoryMixin):
    class Meta:
        model = "geo_areas.GeographicalMembership"

    group = factory.SubFactory(GeographicalAreaFactory, area_code=1)
    member = factory.SubFactory(
        GeographicalAreaFactory,
        area_code=factory.LazyFunction(lambda: random.choice([0, 2])),
    )


class GeographicalAreaDescriptionFactory(ValidityFactoryMixin):
    class Meta:
        model = "geo_areas.GeographicalAreaDescription"

    area = factory.SubFactory(GeographicalAreaFactory)
    description = factory.Faker("text", max_nb_chars=500)
