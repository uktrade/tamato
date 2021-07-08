import pytest

from common.tests import factories

pytestmark = pytest.mark.django_db


def test_certificate_type_in_use(in_use_check_respects_deletes):
    assert in_use_check_respects_deletes(
        factories.CertificateTypeFactory,
        "in_use",
        factories.CertificateFactory,
        "certificate_type",
    )


def test_certificate_in_user(in_use_check_respects_deletes):
    assert in_use_check_respects_deletes(
        factories.CertificateFactory,
        "in_use",
        factories.MeasureConditionFactory,
        "required_certificate",
    )


@pytest.mark.parametrize(
    "factory",
    [
        factories.CertificateTypeFactory,
        factories.CertificateFactory,
        factories.CertificateDescriptionFactory,
    ],
)
def test_certificate_update_types(
    factory,
    check_update_validation,
):
    assert check_update_validation(factory)
