import pytest

from common.models.utils import set_current_transaction
from common.tests import factories
from geo_areas import models
from geo_areas import util

pytestmark = pytest.mark.django_db


def test_with_current_description():
    """Tests that, after updating a geo area description,
    with_current_description returns a queryset with one geo area annotated with
    only the latest description."""
    description = factories.GeographicalAreaDescriptionFactory.create(
        description="blarghhh",
    )
    current_description = description.new_version(
        description.transaction.workbasket,
        description="bleurgh",
    )
    set_current_transaction(current_description.transaction)
    qs = util.with_current_description(models.GeographicalArea.objects.current())

    assert qs.count() == 1
    assert qs.first().description == "bleurgh"
