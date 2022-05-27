import datetime

import pytest

from certificates import forms
from common.tests import factories
from common.util import TaricDateRange

pytestmark = pytest.mark.django_db


def test_form_save_creates_new_certificate(
    session_with_workbasket,
):
    """Tests that the certificate create form creates a new certificate, and
    that two certificates of the same type are created with different sid's."""

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

    certificate_b_data = {
        "certificate_type": certificate_type.pk,
        "start_date_0": 2,
        "start_date_1": 2,
        "start_date_2": 2022,
        "description": "A participation certificate",
    }
    form = forms.CertificateCreateForm(
        data=certificate_b_data,
        request=session_with_workbasket,
    )
    certificate_b = form.save(commit=False)

    assert certificate_a.certificate_type == certificate_b.certificate_type
    assert certificate_a.sid != certificate_b.sid
    assert certificate_b.sid == "002"


def test_certificate_type_does_not_increment_id(
    session_with_workbasket,
):
    """Tests that when two certificates are made with different types, the sids
    are not incremented."""

    certificate_type_a = factories.CertificateTypeFactory.create()
    certificate_type_b = factories.CertificateTypeFactory.create()

    certificates = [
        {
            "certificate_type": certificate_type_a.pk,
            "start_date_0": 2,
            "start_date_1": 2,
            "start_date_2": 2022,
            "description": "certificate 1",
        },
        {
            "certificate_type": certificate_type_b.pk,
            "start_date_0": 2,
            "start_date_1": 2,
            "start_date_2": 2022,
            "description": "certificate 2",
        },
    ]
    completed_certificates = []

    for certificate in certificates:
        form = forms.CertificateCreateForm(
            data=certificate,
            request=session_with_workbasket,
        )
        saved_certificate = form.save(commit=False)
        completed_certificates.append(saved_certificate)

    assert (
        completed_certificates[0].certificate_type
        != completed_certificates[1].certificate_type
    )
    assert completed_certificates[0].sid == "001"
    assert completed_certificates[1].sid == "001"


def test_certificate_create_form_validates_data(session_with_workbasket):
    """A test to check that the create form validates data and ciphers out
    incorrect submissions."""

    certificate_data = {
        "certificate_type": "I am not right",
        "start_date_0": 2,
        "start_date_1": 13,
        "start_date_2": 2022,
        "description": "A participation certificate",
    }
    form = forms.CertificateCreateForm(
        data=certificate_data,
        request=session_with_workbasket,
    )
    error_string = [
        "Select a valid choice. That choice is not one of the available choices.",
    ]
    date_error_string = [
        "Month must be in 1..12",
    ]
    assert form.errors["certificate_type"] == error_string
    assert form.errors["start_date"] == date_error_string
    assert not form.is_valid()
