import pytest
from django.db import DataError

from certificates import business_rules
from common.business_rules import BusinessRuleViolation
from common.models.utils import override_current_transaction
from common.tests import factories

pytestmark = pytest.mark.django_db


@pytest.mark.business_rules
def test_CET1(assert_handles_duplicates):
    """The type of the Certificate must be unique."""

    assert_handles_duplicates(
        factories.CertificateTypeFactory,
        business_rules.CET1,
    )


@pytest.mark.business_rules
def test_CET2(delete_record):
    """The Certificate type cannot be deleted if it is used in a Certificate."""

    certificate = factories.CertificateFactory.create()

    with pytest.raises(BusinessRuleViolation):
        business_rules.CET2(certificate.transaction).validate(
            delete_record(certificate.certificate_type),
        )


@pytest.mark.business_rules
def test_CET3(date_ranges):
    """The start date must be less than or equal to the end date."""

    with pytest.raises(DataError):
        factories.CertificateTypeFactory.create(valid_between=date_ranges.backwards)


@pytest.mark.business_rules
@pytest.mark.xfail(reason="CE2 disabled")
def test_CE2(assert_handles_duplicates):
    """The combination of certificate type and code must be unique."""

    assert_handles_duplicates(
        factories.CertificateFactory,
        business_rules.CE2,
        identifying_fields=("sid", "certificate_type"),
    )


@pytest.mark.business_rules
def test_CE3(date_ranges):
    """The start date must be less than or equal to the end date."""

    with pytest.raises(DataError):
        factories.CertificateFactory.create(valid_between=date_ranges.backwards)


@pytest.mark.business_rules
def test_CE4(assert_spanning_enforced):
    """If a certificate is used in a measure condition then the validity period
    of the certificate must span the validity period of the measure."""

    assert_spanning_enforced(
        factories.CertificateFactory,
        business_rules.CE4,
        measurecondition=factories.related_factory(
            factories.MeasureConditionFactory,
            factory_related_name="required_certificate",
        ),
    )


@pytest.mark.business_rules
def test_CE5(delete_record):
    """The certificate cannot be deleted if it is used in a measure
    condition."""

    condition = factories.MeasureConditionWithCertificateFactory.create()

    with pytest.raises(BusinessRuleViolation):
        business_rules.CE5(condition.transaction).validate(
            delete_record(condition.required_certificate),
        )


@pytest.mark.business_rules
def test_CE6_one_description_mandatory():
    """At least one description record is mandatory."""
    certificate = factories.CertificateFactory.create(description=None)
    with override_current_transaction(certificate.transaction):
        with pytest.raises(BusinessRuleViolation):
            # certificate created without description
            business_rules.CE6(certificate.transaction).validate(certificate)


@pytest.mark.business_rules
def test_CE6_first_description_must_have_same_start_date(date_ranges):
    """The start date of the first description period must be equal to the start
    date of the certificate."""

    description = factories.CertificateDescriptionFactory.create(
        described_certificate__valid_between=date_ranges.no_end,
        validity_start=date_ranges.later.lower,
    )
    with override_current_transaction(description.transaction):
        with pytest.raises(BusinessRuleViolation):
            business_rules.CE6(description.transaction).validate(
                description.described_certificate,
            )


@pytest.mark.business_rules
def test_CE6_start_dates_cannot_match():
    """No two associated description periods for the same certificate and
    language may have the same start date."""

    existing = factories.CertificateDescriptionFactory.create()
    new_description = factories.CertificateDescriptionFactory.create(
        described_certificate=existing.described_certificate,
        validity_start=existing.validity_start,
    )
    with override_current_transaction(new_description.transaction):
        with pytest.raises(BusinessRuleViolation):
            business_rules.CE6(new_description.transaction).validate(
                existing.described_certificate,
            )


@pytest.mark.business_rules
def test_CE6_certificate_validity_period_must_span_description(date_ranges):
    """The validity period of the certificate must span the validity period of
    the certificate description."""

    description = factories.CertificateDescriptionFactory.create(
        described_certificate__valid_between=date_ranges.normal,
        validity_start=date_ranges.overlap_normal.lower,
    )
    with override_current_transaction(description.transaction):
        with pytest.raises(BusinessRuleViolation):
            business_rules.CE6(description.transaction).validate(
                description.described_certificate,
            )


@pytest.mark.business_rules
def test_CE7(assert_spanning_enforced):
    """The validity period of the certificate type must span the validity period
    of the certificate."""

    assert_spanning_enforced(
        factories.CertificateFactory,
        business_rules.CE7,
    )
