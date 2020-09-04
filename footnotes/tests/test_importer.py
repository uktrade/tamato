import pytest

from common.tests import factories
from common.tests.util import validate_taric_import
from footnotes import serializers

pytestmark = pytest.mark.django_db


@validate_taric_import(
    serializers.FootnoteTypeSerializer, factories.FootnoteTypeFactory
)
def test_footnote_type_importer_create(valid_user, test_object, db_object):
    assert db_object.footnote_type_id == test_object.footnote_type_id
    assert db_object.application_code == test_object.application_code
    assert db_object.valid_between.lower == test_object.valid_between.lower
    assert db_object.valid_between.upper == test_object.valid_between.upper


@validate_taric_import(
    serializers.FootnoteSerializer,
    factories.FootnoteFactory,
    dependencies={"footnote_type": factories.FootnoteTypeFactory},
)
def test_footnote_importer_create(valid_user, test_object, db_object):
    assert db_object.footnote_id == test_object.footnote_id
    assert db_object.footnote_type == test_object.footnote_type
    assert db_object.valid_between.lower == test_object.valid_between.lower
    assert db_object.valid_between.upper == test_object.valid_between.upper


@validate_taric_import(
    serializers.FootnoteDescriptionSerializer,
    factories.FootnoteDescriptionFactory,
    dependencies={"described_footnote": factories.FootnoteFactory},
)
def test_footnote_description_importer_create(valid_user, test_object, db_object):
    assert db_object.description_period_sid == test_object.description_period_sid
    assert db_object.description == test_object.description
    assert db_object.described_footnote == test_object.described_footnote
    assert db_object.valid_between.lower == test_object.valid_between.lower
    assert db_object.valid_between.upper == test_object.valid_between.upper
