import pytest

from common.tests import factories

pytestmark = pytest.mark.django_db


def test_add_footnote_on_measure_update(client, valid_user, use_update_form):
    client.force_login(valid_user)
    area = factories.GeographicalAreaFactory.create(area_code=1, area_id=1011)
    measure = factories.MeasureFactory.create(geographical_area=area)
    footnote = factories.FootnoteFactory.create()
    new_data = {"footnotes": lambda d: d + [footnote.pk]}
    use_update_form(measure, new_data)


def test_remove_footnote_on_measure_update():
    pass
