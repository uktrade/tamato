"""Factory classes for BDD tests."""
import factory


class FootnoteFactory(factory.django.DjangoModelFactory):
    """Footnote factory."""

    class Meta:
        model = "footnotes.Footnote"

    description = factory.Faker("paragraph")
