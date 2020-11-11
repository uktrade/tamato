from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

from common.util import validity_range_contains_range
from common.validators import UpdateType

CERTIFICATE_TYPE_SID_REGEX = r"^[A-Z0-9]{1}$"
certificate_type_sid_validator = RegexValidator(CERTIFICATE_TYPE_SID_REGEX)

CERTIFICATE_SID_REGEX = r"^[A-Z0-9]{3}$"
certificate_sid_validator = RegexValidator(CERTIFICATE_SID_REGEX)


def validate_description_is_not_null(certificate_description):
    if not certificate_description.description:
        raise ValidationError({"description": "A description cannot be blank"})


def validate_certificate_type_validity_includes_certificate_validity(certificate):
    """
    CE7
    """
    type_validity = certificate.certificate_type.valid_between
    certificate_validity = certificate.valid_between

    if not validity_range_contains_range(type_validity, certificate_validity):
        raise ValidationError(
            {
                "valid_between": "Certificate type validity period must encompass "
                "the entire certificate validity period"
            }
        )


def validate_certificate_validity_includes_certificate_description_validity(
    certificate_description,
):
    """
    CE6
    """
    certificate_validity = certificate_description.certificate.valid_between
    description_validity = certificate_description.valid_between

    if not validity_range_contains_range(certificate_validity, description_validity):
        raise ValidationError(
            {
                "valid_between": "Certificate validity period must encompass "
                "the entire certificate description validity period"
            }
        )


def validate_first_certificate_description_has_certificate_start_date(
    certificate_description,
):
    """
    CE6
    """
    certificate = certificate_description.described_certificate

    if (
        certificate.descriptions.count() == 0
        and certificate.valid_between.lower
        != certificate_description.valid_between.lower
    ):
        raise ValidationError(
            {
                "valid_between": f"The first description for certificate {certificate} "
                f"must have the same start date as the certificate"
            }
        )


def validate_certificate_description_dont_have_same_start_date(certificate_description):
    """
    CE6
    """
    certificate = certificate_description.described_certificate

    if certificate.descriptions.filter(
        valid_between__startswith=certificate_description.valid_between.lower
    ).exists():
        raise ValidationError(
            {
                "valid_between": f"Certificate {certificate} cannot have two descriptions with the same start date"
            }
        )


def validate_previous_certificate_description_is_adjacent(certificate_description):
    """
    Ensure the previous certificate description is adjacent to the current description.

    There must be no period where there is no description for the certificate.
    """
    if (
        not certificate_description.version_group.current_version
        and certificate_description.update_type == UpdateType.CREATE
    ):
        return

    if (
        certificate_description.version_group.current_version.valid_between.upper
        != certificate_description.valid_between.lower
    ):
        raise ValidationError(
            {
                "valid_between": "Certificate description validity must be "
                "adjacent to the previous descriptions validity"
            }
        )


def validate_at_least_one_description(certificate):
    if certificate.descriptions.count() < 1:
        raise ValidationError("At least one description record is mandatory.")
