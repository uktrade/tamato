import datetime

import factory
import pytest
from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError

from certificates import forms
from certificates import models
from common.tests import factories
from common.tests.util import date_post_data
from common.tests.util import raises_if
from common.tests.util import validity_period_post_data
from common.util import TaricDateRange

pytestmark = pytest.mark.django_db


def test_form_save_creates_new_certificate_sid_and_certificate_type_sid_combo(
    session_with_workbasket,
):
    """Tests that two certificates of the same type are created with different
    sid's."""

    certificate_type = factories.CertificateTypeFactory.create()
    valid_between = TaricDateRange(
        datetime.date(2021, 1, 1),
        datetime.date(2021, 12, 1),
    )
    certificate_a = factories.CertificateFactory.create(
        certificate_type=certificate_type,
        valid_between=valid_between,
        sid="001",
    )

    data = {
        "certificate_type": certificate_type.pk,
        "start_date_0": 2,
        "start_date_1": 2,
        "start_date_2": 2022,
        "description": "A participation certificate",
    }
    form = forms.CertificateCreateForm(data=data, request=session_with_workbasket)
    certificate_b = form.save(commit=False)

    assert certificate_a.sid != certificate_b.sid


@pytest.mark.parametrize(
    ("new_data", "expected_valid"),
    (
        (lambda data: {}, False),
        (
            lambda data: {
                "description": "Test description",
                "certificate_type": "Z",
                "valid_between": validity_period_post_data(
                    datetime.date.today(),
                    datetime.date.today() + relativedelta(months=+1),
                ),
                **date_post_data("start_date", datetime.date.today()),
                **factory.build(
                    dict,
                    sid="001",
                    certificate_type=factories.CertificateTypeFactory.create().pk,
                    description=factories.CertificateDescriptionFactory.create().pk,
                    FACTORY_CLASS=factories.CertificateFactory,
                ),
            },
            True,
        ),
    ),
)
def test_certificate_create_form(use_create_form, new_data, expected_valid):
    with raises_if(ValidationError, not expected_valid):
        use_create_form(models.Certificate, new_data)
