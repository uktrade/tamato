import datetime

import pytest
from django.urls import reverse

from certificates import models
from certificates.views import CertificateList
from common.tests import factories
from common.tests.util import assert_model_view_renders
from common.tests.util import get_class_based_view_urls_matching_url
from common.tests.util import view_is_subclass
from common.tests.util import view_urlpattern_ids
from common.views import TamatoListView
from common.views import TrackedModelDetailMixin


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


@pytest.mark.parametrize(
    ("view", "url_pattern"),
    get_class_based_view_urls_matching_url(
        "certificates/",
        view_is_subclass(TrackedModelDetailMixin),
    ),
    ids=view_urlpattern_ids,
)
def test_certificate_detail_views(view, url_pattern, valid_user_client):
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
