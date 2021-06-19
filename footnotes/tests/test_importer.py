import pytest

from common.tests import factories

pytestmark = pytest.mark.django_db


def test_footnote_type_importer(imported_fields_match):
    assert imported_fields_match(
        factories.FootnoteTypeFactory,
    )


def test_footnote_importer(imported_fields_match):
    assert imported_fields_match(
        factories.FootnoteFactory,
        dependencies={"footnote_type": factories.FootnoteTypeFactory},
    )


def test_footnote_description_importer(imported_fields_match):
    assert imported_fields_match(
        factories.FootnoteDescriptionFactory,
        dependencies={"described_footnote": factories.FootnoteFactory},
    )
