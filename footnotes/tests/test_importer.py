import pytest

from common.tests import factories
from common.tests.util import generate_test_import_xml
from common.validators import UpdateType
from footnotes import models
from footnotes import serializers
from importer.management.commands.import_taric import import_taric
from workbaskets.models import WorkflowStatus

pytestmark = pytest.mark.django_db


def test_footnote_type_importer_create(valid_user):
    footnote_type = factories.FootnoteTypeFactory.build(
        update_type=UpdateType.CREATE.value
    )
    xml = generate_test_import_xml(
        serializers.FootnoteTypeSerializer(
            footnote_type, context={"format": "xml"}
        ).data
    )

    import_taric(xml, valid_user.username, WorkflowStatus.PUBLISHED.value)

    db_footnote_type = models.FootnoteType.objects.get(
        footnote_type_id=footnote_type.footnote_type_id
    )

    assert db_footnote_type.footnote_type_id == footnote_type.footnote_type_id
    assert db_footnote_type.application_code == footnote_type.application_code
    assert db_footnote_type.valid_between.lower == footnote_type.valid_between.lower
    assert db_footnote_type.valid_between.upper == footnote_type.valid_between.upper
