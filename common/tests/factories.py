"""Factory classes for BDD tests."""
from datetime import datetime
from datetime import timezone

import factory
from psycopg2.extras import DateTimeTZRange


BREXIT_DATE = datetime(2021, 1, 1).replace(tzinfo=timezone.utc)


class ValidityFactoryMixin(factory.django.DjangoModelFactory):
    valid_between = factory.LazyFunction(lambda: DateTimeTZRange(BREXIT_DATE, None))


class FootnoteTypeFactory(ValidityFactoryMixin):
    """FootnoteType factory."""

    class Meta:
        model = "footnotes.FootnoteType"

    id = factory.Sequence(lambda n: f"{n:02d}")
    application_code = factory.Faker("random_int")
    description = factory.Faker("paragraph")


class FootnoteFactory(ValidityFactoryMixin):
    """Footnote factory."""

    class Meta:
        model = "footnotes.Footnote"

    id = factory.Sequence(lambda n: f"{n:05d}")
    footnote_type = factory.SubFactory(FootnoteTypeFactory)


class UserFactory(factory.django.DjangoModelFactory):
    """User factory."""

    class Meta:
        model = "auth.User"
