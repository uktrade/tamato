import pytest

from common.tests import factories
from footnotes import serializers

pytestmark = pytest.mark.django_db


def test_footnote_type_importer(imported_fields_match):
    assert imported_fields_match(
        factories.FootnoteTypeFactory,
        serializers.FootnoteTypeSerializer,
    )


def test_footnote_importer(imported_fields_match):
    assert imported_fields_match(
        factories.FootnoteFactory,
        serializers.FootnoteSerializer,
        dependencies={"footnote_type": factories.FootnoteTypeFactory},
    )


def test_footnote_description_importer(imported_fields_match):
    assert imported_fields_match(
        factories.FootnoteDescriptionFactory,
        serializers.FootnoteDescriptionSerializer,
        dependencies={"described_footnote": factories.FootnoteFactory},
    )
