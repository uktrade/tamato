"""Factory classes for BDD tests."""
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
    description = factory.Faker("text", max_nb_chars=500)


class FootnoteFactory(ValidityFactoryMixin):
    """Footnote factory."""

    class Meta:
        model = "footnotes.Footnote"

    footnote_id = factory.Sequence(lambda n: f"{n:03d}")
    description = factory.Faker("text", max_nb_chars=500)
    footnote_type = factory.SubFactory(FootnoteTypeFactory)


class UserFactory(factory.django.DjangoModelFactory):
    """User factory."""

    class Meta:
        model = "auth.User"
