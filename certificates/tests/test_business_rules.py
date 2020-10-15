from datetime import datetime
from datetime import timezone

import pytest
from django.core.exceptions import ValidationError
from django.db import DataError
from django.db import IntegrityError
from psycopg2._range import DateTimeTZRange

from common.tests import factories


pytestmark = pytest.mark.django_db


def test_cet1():
    """
    The type of the Certificate must be unique
    """
    t = factories.CertificateTypeFactory.create()

    with pytest.raises(IntegrityError):
        factories.CertificateTypeFactory.create(sid=t.sid)


def test_cet2():
    """
    The Certificate type cannot be deleted if it is used in a Certificate
    """
    t = factories.CertificateTypeFactory.create()
    factories.CertificateFactory.create(certificate_type=t)

    with pytest.raises(IntegrityError):
        t.delete()


def test_cet3(date_ranges):
    """
    The start date must be less than or equal to the end date
    """
    with pytest.raises(DataError):
        factories.CertificateTypeFactory.create(valid_between=date_ranges.backwards)


def test_ce2():
    """
    The combination certificate type and code must be unique.
    """
    t = factories.CertificateTypeFactory.create()
    certificate = factories.CertificateFactory.create(certificate_type=t)
    factories.CertificateFactory.create(sid=certificate.sid)

    with pytest.raises(IntegrityError):
        factories.CertificateFactory.create(sid=certificate.sid, certificate_type=t)


def test_ce3(date_ranges):
    """
    The start date must be less than or equal to the end date
    """
    with pytest.raises(DataError):
        factories.CertificateFactory.create(valid_between=date_ranges.backwards)


def test_ce4(date_ranges):
    """
    If a certificate is used in a measure condition then the validity period of the certificate
    must span the validity period of the measure
    """

    with pytest.raises(ValidationError):
        factories.MeasureConditionFactory(
            required_certificate=factories.CertificateFactory(
                valid_between=date_ranges.starts_with_normal,
            ),
            dependent_measure__valid_between=date_ranges.normal,
        )


def test_ce5(approved_workbasket):
    """
    When a certificate cannot be deleted if it is used in a measure condition
    """

    condition = factories.MeasureConditionFactory(
        required_certificate=factories.CertificateFactory(),
        workbasket=approved_workbasket,
    )

    with pytest.raises(IntegrityError):
        condition.required_certificate.delete()


def test_ce6_one_description_mandatory():
    """
    At least one description record is mandatory
    """

    workbasket = factories.WorkBasketFactory()
    factories.CertificateFactory(workbasket=workbasket)

    with pytest.raises(ValidationError):
        workbasket.submit_for_approval()


def test_ce6_first_description_must_have_same_start_date(date_ranges):
    """
    The start date of the first description period must be equal to the start date of the certificate
    """
    certificate = factories.CertificateFactory(valid_between=date_ranges.no_end)

    with pytest.raises(ValidationError):
        factories.CertificateDescriptionFactory(
            described_certificate=certificate, valid_between=date_ranges.later
        )


def test_ce6_start_dates_cannot_match(date_ranges):
    """
    No two associated description periods for the same certificate and language may have the same start date
    """
    certificate = factories.CertificateFactory(valid_between=date_ranges.no_end)

    factories.CertificateDescriptionFactory(
        described_certificate=certificate, valid_between=date_ranges.no_end
    )
    with pytest.raises(ValidationError):
        factories.CertificateDescriptionFactory(
            described_certificate=certificate, valid_between=date_ranges.no_end
        )


def test_ce6_certificate_validity_period_must_span_description(date_ranges):
    """
    The validity period of the certificate must span the validity period of the certificate description
    """
    certificate = factories.CertificateFactory(valid_between=date_ranges.normal)
    with pytest.raises(ValidationError):
        factories.CertificateDescriptionFactory(
            described_certificate=certificate, valid_between=date_ranges.overlap_normal
        )


def test_ce7(date_ranges):
    """
    The validity period of the certificate type must span the validity period of the certificate.
    """
    t = factories.CertificateTypeFactory(valid_between=date_ranges.normal)
    with pytest.raises(ValidationError):
        factories.CertificateFactory(
            certificate_type=t, valid_between=date_ranges.overlap_normal
        )


def test_certificate_description_periods_cannot_overlap(date_ranges):
    """
    Ensure validity periods for descriptions with a given SID cannot overlap.
    """
    first = factories.CertificateDescriptionFactory(
        sid=10000,
        valid_between=date_ranges.normal,
        described_certificate__valid_between=date_ranges.no_end,
    )
    with pytest.raises(IntegrityError):
        factories.CertificateDescriptionFactory(
            sid=10000,
            valid_between=date_ranges.overlap_normal,
            described_certificate=first.described_certificate,
        )


def test_certificate_description_period_must_be_adjacent_to_predecessor(date_ranges):
    """
    Ensure validity periods for successive descriptions must be adjacent.
    """
    predecessor = factories.CertificateDescriptionFactory(
        valid_between=date_ranges.normal,
        described_certificate__valid_between=date_ranges.no_end,
    )
    predecessor = factories.CertificateDescriptionFactory(
        sid=predecessor.sid,
        predecessor=predecessor,
        described_certificate=predecessor.described_certificate,
        valid_between=date_ranges.adjacent_later,
    )
    with pytest.raises(ValidationError):
        factories.CertificateDescriptionFactory(
            sid=predecessor.sid,
            predecessor=predecessor,
            described_certificate=predecessor.described_certificate,
            valid_between=date_ranges.adjacent_even_later,
        )
