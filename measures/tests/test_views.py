import pytest
from django.urls import reverse

from common.tests import factories
from common.validators import UpdateType
from measures.models import FootnoteAssociationMeasure
from measures.models import Measure

pytestmark = pytest.mark.django_db


def test_add_footnotes_on_measure_edit(
    client,
    valid_user,
    existing_measure,
    existing_measure_data,
):
    footnote1 = factories.FootnoteFactory.create()
    footnote2 = factories.FootnoteFactory.create()
    factories.GeographicalAreaFactory(area_code=1, area_id=1011)
    edit_url = reverse("measure-ui-edit", args=[existing_measure.sid])
    existing_measure_data.update(footnotes=[f"|{footnote1.pk}|{footnote2.pk}|"])

    assert existing_measure.footnotes.count() == 0

    client.force_login(valid_user)
    response = client.post(edit_url, data=existing_measure_data)

    assert response.status_code == 302

    new_version = Measure.objects.exclude(pk=existing_measure.pk).get(
        version_group=existing_measure.version_group,
    )

    assert new_version.footnotes.count() == 2


def test_remove_footnote_on_measure_edit(
    client,
    valid_user,
    existing_measure,
    existing_measure_data,
):
    footnote = factories.FootnoteFactory.create()
    FootnoteAssociationMeasure.objects.create(
        footnoted_measure=existing_measure,
        associated_footnote=footnote,
        update_type=UpdateType.CREATE,
        transaction=existing_measure.transaction,
    )

    assert existing_measure.footnotes.count() == 1

    edit_url = reverse("measure-ui-edit", args=[existing_measure.sid])
    factories.GeographicalAreaFactory(area_code=1, area_id=1011)
    existing_measure_data.update(footnotes=[])
    client.force_login(valid_user)
    response = client.post(edit_url, data=existing_measure_data)

    assert response.status_code == 302

    new_version = Measure.objects.exclude(pk=existing_measure.pk).get(
        version_group=existing_measure.version_group,
    )

    assert new_version.footnotes.count() == 0
