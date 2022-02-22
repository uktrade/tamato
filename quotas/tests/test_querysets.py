import pytest

from common.tests import factories

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("number_of_certificates, is_origin_quota"),
    ((0, False), (1, True)),
)
def test_with_is_origin_quota(number_of_certificates, is_origin_quota: bool):
    """
    Adds a number of required certificates to a QuotaOrderNumberFactory.

    After creating an instance of the model, checks whether it is marked as an
    origin quota.
    """

    model_factory = factories.QuotaOrderNumberFactory.create(
        required_certificates=[
            factories.CertificateFactory.create()
            for _ in range(0, number_of_certificates)
        ],
    )

    test_instance = model_factory._meta.model.objects.with_is_origin_quota().get()
    assert test_instance.origin_quota == is_origin_quota
