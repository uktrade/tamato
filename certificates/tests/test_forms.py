import datetime

import pytest

from certificates import forms
from common.tests import factories
from common.util import TaricDateRange

pytestmark = pytest.mark.django_db


def test_form_save_creates_new_certificate(
    session_request_with_workbasket,
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
        request=session_request_with_workbasket,
    )
    certificate_b = form.save(commit=False)

    assert certificate_a.certificate_type == certificate_b.certificate_type
    assert certificate_a.sid != certificate_b.sid
    assert certificate_b.sid == "002"


def test_certificate_type_does_not_increment_id(
    session_request_with_workbasket,
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
            request=session_request_with_workbasket,
        )
        saved_certificate = form.save(commit=False)
        completed_certificates.append(saved_certificate)

    assert (
        completed_certificates[0].certificate_type
        != completed_certificates[1].certificate_type
    )
    assert completed_certificates[0].sid == "001"
    assert completed_certificates[1].sid == "001"


def test_certificate_create_form_validates_data(session_request_with_workbasket):
    """A test to check that the create form validates data and ciphers out
    incorrect submissions."""

    certificate_data = {
        "certificate_type": "I am not right",
        "sid": "<bad_code></>",
        "start_date_0": 2,
        "start_date_1": 13,
        "start_date_2": 2022,
        "description": "A participation certificate",
    }
    form = forms.CertificateCreateForm(
        data=certificate_data,
        request=session_request_with_workbasket,
    )
    error_string = [
        "Select a valid choice. That choice is not one of the available choices.",
    ]
    date_error_string = [
        "Month must be in 1..12",
    ]
    sid_validation_error_string = [
        "Only alphanumeric characters are allowed.",
    ]
    assert form.errors["certificate_type"] == error_string
    assert form.errors["start_date"] == date_error_string
    assert form.errors["sid"] == sid_validation_error_string

    assert not form.is_valid()


def test_certificate_create_with_custom_sid(session_request_with_workbasket):
    """Tests that a certificate can be created with a custom sid inputted by the
    user."""
    certificate_type = factories.CertificateTypeFactory.create()
    data = {
        "certificate_type": certificate_type.pk,
        "start_date_0": 2,
        "start_date_1": 2,
        "start_date_2": 2022,
        "description": "A participation certificate",
        "sid": "A01",
    }
    form = forms.CertificateCreateForm(
        data=data,
        request=session_request_with_workbasket,
    )
    certificate = form.save(commit=False)

    assert certificate.sid == "A01"


def test_certificate_create_ignores_non_numeric_sid(session_request_with_workbasket):
    """Tests that a certificate is created with a numeric sid when a certificate
    of the same type with a non-numeric sid already exists."""
    certificate_type = factories.CertificateTypeFactory.create()
    factories.CertificateFactory.create(certificate_type=certificate_type, sid="A01")
    data = {
        "certificate_type": certificate_type.pk,
        "start_date_0": 2,
        "start_date_1": 2,
        "start_date_2": 2022,
        "description": "A participation certificate",
    }
    form = forms.CertificateCreateForm(
        data=data,
        request=session_request_with_workbasket,
    )
    certificate = form.save(commit=False)

    assert certificate.sid == "001"


def test_validation_error_raised_for_duplicate_sid(session_request_with_workbasket):
    """Tests that a validation error is raised on create when a certificate of
    the same type with the same sid already exists."""
    certificate_type = factories.CertificateTypeFactory.create()
    factories.CertificateFactory.create(certificate_type=certificate_type, sid="A01")
    data = {
        "certificate_type": certificate_type.pk,
        "start_date_0": 2,
        "start_date_1": 2,
        "start_date_2": 2022,
        "description": "A participation certificate",
        "sid": "A01",
    }
    form = forms.CertificateCreateForm(
        data=data,
        request=session_request_with_workbasket,
    )

    assert not form.is_valid()
    assert (
        f"Certificate with sid A01 and type {certificate_type} already exists."
        in form.errors["sid"]
    )


def test_certificate_description_valid_data():
    certificate = factories.CertificateFactory.create()
    data = {
        "described_certificate": certificate.pk,
        "description": "certifiably certified",
        "validity_start_0": 1,
        "validity_start_1": 1,
        "validity_start_2": 2022,
    }
    form = forms.CertificateCreateDescriptionForm(data=data)

    assert form.is_valid()


def test_certificate_description_invalid_data():
    form = forms.CertificateCreateDescriptionForm(data={})

    assert not form.is_valid()
    assert "This field is required." in form.errors["described_certificate"]
    assert "This field is required." in form.errors["description"]
    assert "Enter the day, month and year" in form.errors["validity_start"]
