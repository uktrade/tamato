import datetime

import pytest
from django.urls import reverse

from certificates import models
from certificates.views import CertificateDescriptionCreate
from certificates.views import CertificateList
from common.models.utils import override_current_transaction
from common.tests import factories
from common.tests.util import assert_model_view_renders
from common.tests.util import assert_read_only_model_view_returns_list
from common.tests.util import get_class_based_view_urls_matching_url
from common.tests.util import view_is_subclass
from common.tests.util import view_urlpattern_ids
from common.views import TamatoListView
from common.views import TrackedModelDetailMixin

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "factory",
    (factories.CertificateFactory, factories.CertificateDescriptionFactory),
)
def test_certificate_delete(factory, use_delete_form):
    use_delete_form(factory())


def test_certificate_create_form_creates_certificate_description_object(
    valid_user_api_client,
):

    # Post a form
    create_url = reverse("certificate-ui-create")

    certificate_type = factories.CertificateTypeFactory.create()
    form_data = {
        "certificate_type": certificate_type.pk,
        "start_date_0": 2,
        "start_date_1": 2,
        "start_date_2": 2022,
        "description": "A participation certificate",
    }

    valid_user_api_client.post(create_url, form_data)
    #  get the certificate we have made, and the certificate description matching our description on the form
    certificate = models.Certificate.objects.all()[0]
    certificate_description = models.CertificateDescription.objects.filter(
        description=form_data["description"],
    )[0]

    assert certificate.sid == certificate_description.described_certificate.sid
    assert certificate_description.validity_start == datetime.date(2022, 2, 2)
    assert certificate.transaction == certificate_description.transaction


@pytest.mark.parametrize(
    ("view", "url_pattern"),
    get_class_based_view_urls_matching_url(
        "certificates/",
        view_is_subclass(TrackedModelDetailMixin),
    ),
    ids=view_urlpattern_ids,
)
def test_certificate_detail_views(
    view,
    url_pattern,
    valid_user_client,
    session_with_workbasket,
):
    """Verify that certificate detail views are under the url certificates/ and
    don't return an error."""
    model_overrides = {
        "certificates.views.CertificateDescriptionCreate": models.Certificate,
    }

    assert_model_view_renders(view, url_pattern, valid_user_client, model_overrides)


@pytest.mark.parametrize(
    ("view", "url_pattern"),
    get_class_based_view_urls_matching_url(
        "certificates/",
        view_is_subclass(TamatoListView),
        assert_contains_view_classes=[CertificateList],
    ),
    ids=view_urlpattern_ids,
)
def test_certificate_list_view(view, url_pattern, valid_user_client):
    """Verify that certificate list view is under the url certificates/ and
    doesn't return an error."""
    assert_model_view_renders(view, url_pattern, valid_user_client)


# https://uktrade.atlassian.net/browse/TP2000-450 /PS-IGNORE
def test_description_create_get_initial():
    """Test that, where more than one version of a certificate exists,
    get_initial returns only the current version."""
    certificate = factories.CertificateFactory.create()
    new_version = certificate.new_version(certificate.transaction.workbasket)
    view = CertificateDescriptionCreate(
        kwargs={
            "certificate_type__sid": certificate.certificate_type.sid,
            "sid": certificate.sid,
        },
    )
    with override_current_transaction(new_version.transaction):
        initial = view.get_initial()

        assert initial["described_certificate"] == new_version


def test_description_create_get_context_data(valid_user_api_client):
    """Test that posting to certificate create endpoint with valid data returns
    a 302 and creates new description matching certificate."""
    certificate = factories.CertificateFactory.create(description=None)
    new_version = certificate.new_version(certificate.transaction.workbasket)
    url = reverse(
        "certificate-ui-description-create",
        args=(certificate.certificate_type.sid, certificate.sid),
    )
    post_data = {
        "description": "certifiably certified",
        "described_certificate": new_version.pk,
        "validity_start_0": 1,
        "validity_start_1": 1,
        "validity_start_2": 2022,
    }
    assert not models.CertificateDescription.objects.exists()
    response = valid_user_api_client.post(url, post_data)

    assert response.status_code == 302
    assert models.CertificateDescription.objects.filter(
        described_certificate__sid=new_version.sid,
        described_certificate__certificate_type__sid=new_version.certificate_type.sid,
    ).exists()


def test_certificate_api_list_view(valid_user_client, date_ranges):
    selected_type = factories.CertificateTypeFactory.create()
    expected_results = [
        factories.CertificateFactory.create(
            valid_between=date_ranges.normal,
            certificate_type=selected_type,
        ),
        factories.CertificateFactory.create(
            valid_between=date_ranges.earlier,
            certificate_type=selected_type,
        ),
    ]
    assert_read_only_model_view_returns_list(
        "certificate",
        "value",
        "pk",
        expected_results,
        valid_user_client,
    )


def test_certificate_type_api_list_view(valid_user_client):
    expected_results = [
        factories.CertificateTypeFactory.create(),
    ]

    assert_read_only_model_view_returns_list(
        "certificatetype",
        "sid",
        "sid",
        expected_results,
        valid_user_client,
    )
