import pytest
from pytest_bdd import given

from common.tests import factories

pytestmark = pytest.mark.django_db


@given("certificate X000", target_fixture="certificate_X000")
def certificate_X000(date_ranges):
    desc = factories.CertificateDescriptionFactory.create(
        described_certificate=factories.CertificateFactory.create(
            certificate_type=factories.CertificateTypeFactory.create(
                sid="X",
            ),
            sid="000",
        ),
        description="This is X000",
    )
    return desc.described_certificate
