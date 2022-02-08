import datetime

import factory
import pytest
from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError

from common.tests import factories
from common.tests.util import date_post_data
from common.tests.util import raises_if
from common.tests.util import validity_period_post_data
from common.util import TaricDateRange
from footnotes import forms
from footnotes import models

pytestmark = pytest.mark.django_db

# https://uktrade.atlassian.net/browse/TP-851
def test_form_save_creates_new_footnote_id_and_footnote_type_id_combo(session_request):
    """Tests that when two non-overlapping footnotes of the same type are
    created that these are created with a different footnote_id, to avoid
    duplication of footnote_id and footnote_type_id combination e.g. TN001."""
    footnote_type = factories.FootnoteTypeFactory.create()
    valid_between = TaricDateRange(
        datetime.date(2021, 1, 1),
        datetime.date(2021, 12, 1),
    )
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
    form = forms.FootnoteCreateForm(data=data, request=session_request)
    new_footnote = form.save(commit=False)

    assert earlier.footnote_id != new_footnote.footnote_id


@pytest.mark.parametrize(
    ("new_data", "expected_valid"),
    (
        (lambda data: {}, False),
        (
            lambda data: {
                "description": "Test description",
                "footnote_type": "CN",
                "valid_between": validity_period_post_data(
                    datetime.date.today(),
                    datetime.date.today() + relativedelta(months=+1),
                ),
                **date_post_data("start_date", datetime.date.today()),
                **factory.build(
                    dict,
                    footnote_id="001",
                    footnote_type=factories.FootnoteTypeFactory.create().pk,
                    description=factories.FootnoteDescriptionFactory.create().pk,
                    FACTORY_CLASS=factories.FootnoteFactory,
                ),
            },
            True,
        ),
    ),
)
def test_footnote_create_form(use_create_form, new_data, expected_valid):
    with raises_if(ValidationError, not expected_valid):
        use_create_form(models.Footnote, new_data)
