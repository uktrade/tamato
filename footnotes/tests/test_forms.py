from datetime import date
from unittest import mock

import pytest

from common.tests import factories
from common.util import TaricDateRange
from footnotes import forms
from workbaskets.validators import WorkflowStatus

pytestmark = pytest.mark.django_db


def test_form_save_creates_new_footnote_id_and_footnote_type_id_combo(client):
    workbasket = factories.WorkBasketFactory.create(
        status=WorkflowStatus.EDITING,
    )
    workbasket.save_to_session(client.session)
    client.session.save()
    footnote_type = factories.FootnoteTypeFactory.create()
    valid_between = TaricDateRange(date(2021, 1, 1), date(2021, 12, 1))

    earlier = factories.FootnoteFactory.create(
        footnote_type=footnote_type,
        valid_between=valid_between,
        footnote_id="001",
    )
    overlapping = factories.FootnoteFactory.create(
        footnote_type=footnote_type,
        valid_between=TaricDateRange(date(2021, 1, 1), date(2022, 3, 3)),
    )

    data = {
        "footnote_type": footnote_type.pk,
        "start_date_0": 2,
        "start_date_1": 2,
        "start_date_2": 2022,
        "description": "A note on feet",
    }
    form = forms.FootnoteCreateForm(data=data)
    form.is_valid()

    with mock.patch("workbaskets.models.WorkBasket.current", return_value=workbasket):
        new_footnote = form.save(commit=False)

    assert earlier.footnote_id != new_footnote.footnote_id
