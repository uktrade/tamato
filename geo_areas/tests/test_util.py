import pytest

from common.tests import factories
from geo_areas import models
from geo_areas import util

pytestmark = pytest.mark.django_db


def test_with_description_returns_description_string():
    factories.GeographicalAreaDescriptionFactory.create(description="Guernsey")
    geo_area = util.with_description_string(
        models.GeographicalArea.objects.all(),
    ).first()

    assert geo_area.description == "Guernsey"
