from datetime import datetime
from datetime import timedelta

import pytest

from common.tests import factories
from geo_areas import models
from geo_areas import util

pytestmark = pytest.mark.django_db


def test_with_latest_description_returns_description_string():
    factories.GeographicalAreaDescriptionFactory.create(description="Guernsey")
    geo_area = util.with_latest_description_string(
        models.GeographicalArea.objects.all(),
    ).first()

    assert geo_area.description == "Guernsey"


def test_with_latest_description_multiple_descriptions():
    """Tests that when a GeographicalArea has more than one description, the
    description with a later validity_start date is used to generate the
    description string."""
    area = factories.GeographicalAreaFactory.create()
    earlier_description = factories.GeographicalAreaDescriptionFactory.create(
        validity_start=datetime.today(),
        described_geographicalarea=area,
    )
    later_description = factories.GeographicalAreaDescriptionFactory.create(
        validity_start=datetime.today() + timedelta(days=1),
        described_geographicalarea=area,
    )
    qs = util.with_latest_description_string(models.GeographicalArea.objects.all())

    assert qs.count() == 1
    assert later_description.description == qs.first().description


def test_with_latest_description_multiple_descriptions_same_date():
    """Tests that when a GeographicalArea has more than one description with the
    same validity start date, the description from the later transaction is used
    to generate the description string."""
    area = factories.GeographicalAreaFactory.create()
    first_description = factories.GeographicalAreaDescriptionFactory.create(
        validity_start=datetime.today(),
        described_geographicalarea=area,
    )
    second_description = factories.GeographicalAreaDescriptionFactory.create(
        validity_start=datetime.today(),
        described_geographicalarea=area,
    )
    qs = util.with_latest_description_string(models.GeographicalArea.objects.all())

    assert qs.count() == 1
    assert second_description.description == qs.first().description
