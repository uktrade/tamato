from datetime import date

import pytest
from django.test.client import RequestFactory

from common.tests import factories
from common.util import TaricDateRange
from footnotes import forms

pytestmark = pytest.mark.django_db

# https://uktrade.atlassian.net/browse/TP-851
def test_form_save_creates_new_footnote_id_and_footnote_type_id_combo(client):
    """Tests that when two non-overlapping footnotes of the same type are
    created that these are created with a different footnote_id, to avoid
    duplication of footnote_id and footnote_type_id combination e.g. TN001."""
    workbasket = factories.ApprovedWorkBasketFactory.create()
    session = client.session
    session.update({"workbasket": {"id": workbasket.pk}})
    session.save()
    request = RequestFactory()
    request.session = session

    footnote_type = factories.FootnoteTypeFactory.create()
    valid_between = TaricDateRange(date(2021, 1, 1), date(2021, 12, 1))
    earlier = factories.FootnoteFactory.create(
        footnote_type=footnote_type,
        valid_between=valid_between,
        footnote_id="001",
    )

    data = {
        "footnote_type": footnote_type.pk,
        "start_date_0": 2,
        "start_date_1": 2,
        "start_date_2": 2022,
        "description": "A note on feet",
    }
    form = forms.FootnoteCreateForm(data=data, request=request)

    # with mock.patch("workbaskets.models.WorkBasket.current", return_value=workbasket):
    new_footnote = form.save(commit=False)

    assert earlier.footnote_id != new_footnote.footnote_id
