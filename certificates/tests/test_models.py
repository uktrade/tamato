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
    ["factory", "description_factory"],
    [
        (factories.CertificateTypeFactory, None),
        (factories.CertificateFactory, factories.CertificateDescriptionFactory),
        (factories.CertificateDescriptionFactory, None),
    ],
)
def test_certificate_update_types(
    factory,
    description_factory,
    check_update_validation,
):
    assert check_update_validation(factory, description_factory=description_factory)
