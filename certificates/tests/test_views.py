import datetime

import pytest
from bs4 import BeautifulSoup
from django.core.exceptions import ValidationError
from django.urls import reverse

from certificates import models
from certificates.views import CertificateDescriptionCreate
from certificates.views import CertificateDetailMeasures
from certificates.views import CertificateList
from common.models.utils import override_current_transaction
from common.tests import factories
from common.tests.util import assert_model_view_renders
from common.tests.util import assert_read_only_model_view_returns_list
from common.tests.util import date_post_data
from common.tests.util import get_class_based_view_urls_matching_url
from common.tests.util import raises_if
from common.tests.util import view_is_subclass
from common.tests.util import view_urlpattern_ids
from common.validators import UpdateType
from common.views import TamatoListView
from common.views import TrackedModelDetailMixin

pytestmark = pytest.mark.django_db


def test_certificate_delete(use_delete_form):
    use_delete_form(factories.CertificateFactory())


def test_certificate_description_delete_form(use_delete_form):
    certificate = factories.CertificateFactory()
    description1, description2 = factories.CertificateDescriptionFactory.create_batch(
        2,
        described_certificate=certificate,
    )
    use_delete_form(description1)
    try:
        use_delete_form(description2)
    except ValidationError as e:
        assert (
            "This description cannot be deleted because at least one description record is mandatory."
            in e.message
        )


def test_certificate_create_form_creates_certificate_description_object(
    api_client_with_current_workbasket,
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

    api_client_with_current_workbasket.post(create_url, form_data)
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
    session_request_with_workbasket,
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


def test_description_create_get_context_data(api_client_with_current_workbasket):
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
    response = api_client_with_current_workbasket.post(url, post_data)

    assert response.status_code == 302
    assert models.CertificateDescription.objects.filter(
        described_certificate__sid=new_version.sid,
        described_certificate__certificate_type__sid=new_version.certificate_type.sid,
    ).exists()


@pytest.mark.parametrize(
    ("data_changes", "expected_valid"),
    (
        ({**date_post_data("start_date", datetime.date.today())}, True),
        (
            {
                "start_date_0": "",
                "start_date_1": "",
                "start_date_2": "",
            },
            False,
        ),
    ),
)
@pytest.mark.parametrize(
    "update_type",
    (
        UpdateType.CREATE,
        UpdateType.UPDATE,
    ),
)
def test_certificate_edit_views(
    data_changes,
    expected_valid,
    update_type,
    use_edit_view,
    workbasket,
    published_certificate_type,
):
    """Tests that certificate edit views (for update types CREATE and UPDATE)
    allows saving a valid form from an existing instance and that an invalid
    form fails validation as expected."""

    certificate = factories.CertificateFactory.create(
        update_type=update_type,
        certificate_type=published_certificate_type,
        transaction=workbasket.new_transaction(),
    )
    with raises_if(ValidationError, not expected_valid):
        use_edit_view(certificate, data_changes)


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


def test_certificate_detail_measures_view(valid_user_client):
    """Test that `CertificateDetailMeasures` view returns 200 and renders
    actions link and other tabs."""
    certificate = factories.CertificateFactory.create()

    url_kwargs = {
        "sid": certificate.sid,
        "certificate_type__sid": certificate.certificate_type.sid,
    }
    details_tab_url = reverse("certificate-ui-detail", kwargs=url_kwargs)
    version_control_tab_url = reverse(
        "certificate-ui-detail-version-control",
        kwargs=url_kwargs,
    )
    measures_tab_url = reverse("certificate-ui-detail-measures", kwargs=url_kwargs)
    descriptions_tab_url = reverse(
        "certificate-ui-detail-descriptions",
        kwargs=url_kwargs,
    )
    expected_tabs = {
        "Details": details_tab_url,
        "Descriptions": descriptions_tab_url,
        "Measures": measures_tab_url,
        "Version control": version_control_tab_url,
    }

    response = valid_user_client.get(measures_tab_url)
    assert response.status_code == 200

    page = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )
    tabs = {tab.text: tab.attrs["href"] for tab in page.select(".govuk-tabs__tab")}
    assert tabs == expected_tabs

    actions = page.find("h2", text="Actions").find_next("a")
    assert actions.text == "View in find and edit measures"
    assert (
        actions.attrs["href"]
        == f"{reverse('measure-ui-list')}?certificates={certificate.pk}"
    )


def test_certificate_detail_measures_view_lists_measures(valid_user_client):
    """Test that `CertificateDetailMeasures` view displays a paginated list of
    measures for a certificate."""
    certificate = factories.CertificateFactory.create()
    measures = []
    for measure_with_condition in range(21):
        measure = factories.MeasureFactory.create()
        factories.MeasureConditionFactory.create(
            dependent_measure=measure,
            required_certificate=certificate,
        )
        measures.append(measure)
    url = reverse(
        "certificate-ui-detail-measures",
        kwargs={
            "sid": certificate.sid,
            "certificate_type__sid": certificate.certificate_type.sid,
        },
    )
    response = valid_user_client.get(url)
    page = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )

    table_rows = page.select(".govuk-table tbody tr")
    assert len(table_rows) == CertificateDetailMeasures.paginate_by

    table_measure_sids = {
        int(sid.text) for sid in page.select(".govuk-table tbody tr td:first-child")
    }
    assert table_measure_sids.issubset({m.sid for m in measures})

    assert page.find("nav", class_="pagination").find_next("a", href="?page=2")


def test_certificate_detail_measures_view_lists_measures_latest_version(
    valid_user_client,
    user_workbasket,
):
    """Test that `CertificateDetailMeasures` view displays a paginated list of
    the latest measures for a certificate when the condition is related to the
    ."""
    certificate = factories.CertificateFactory.create()
    tnx = certificate.transaction
    workbasket = certificate.transaction.workbasket
    measures = []
    new_measures = []
    for measure_with_condition in range(10):
        measure = factories.MeasureFactory.create(
            transaction=tnx,
        )
        factories.MeasureConditionFactory.create(
            dependent_measure=measure,
            required_certificate=certificate,
            transaction=tnx,
        )
        new_measure = measure.new_version(
            workbasket=workbasket,
            update_type=UpdateType.UPDATE,
        )
        measures.append(measure)
        new_measures.append(new_measure)

    url = reverse(
        "certificate-ui-detail-measures",
        kwargs={
            "sid": certificate.sid,
            "certificate_type__sid": certificate.certificate_type.sid,
        },
    )
    response = valid_user_client.get(url)
    page = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )

    table_rows = page.select(".govuk-table tbody tr")
    assert len(table_rows) == 10

    table_measure_sids = {
        int(sid.text) for sid in page.select(".govuk-table tbody tr td:first-child")
    }
    assert table_measure_sids == {m.sid for m in new_measures}


def test_certificate_detail_measures_view_sorting_commodity(valid_user_client):
    """Test that measures listed on `CertificateDetailMeasures` view can be
    sorted by commodity code in ascending or descending order."""
    certificate = factories.CertificateFactory.create()
    measures = []
    for measure_with_condition in range(3):
        measure = factories.MeasureFactory.create()
        factories.MeasureConditionFactory.create(
            dependent_measure=measure,
            required_certificate=certificate,
        )
        measures.append(measure)
    commodity_codes = [measure.goods_nomenclature.item_id for measure in measures]

    url = reverse(
        "certificate-ui-detail-measures",
        kwargs={
            "sid": certificate.sid,
            "certificate_type__sid": certificate.certificate_type.sid,
        },
    )
    response = valid_user_client.get(f"{url}?sort_by=goods_nomenclature&ordered=asc")
    page = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )
    table_commodity_codes = [
        commodity.text
        for commodity in page.select(".govuk-table tbody tr td:nth-child(2) a")
    ]
    assert table_commodity_codes == commodity_codes

    response = valid_user_client.get(f"{url}?sort_by=goods_nomenclature&ordered=desc")
    page = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )
    table_commodity_codes = [
        commodity.text
        for commodity in page.select(".govuk-table tbody tr td:nth-child(2) a")
    ]
    commodity_codes.reverse()
    assert table_commodity_codes == commodity_codes


def test_certificate_detail_measures_view_sorting_start_date(
    date_ranges,
    valid_user_client,
):
    """Test that measures listed on `CertificateDetailMeasures` view can be
    sorted by start date in ascending or descending order."""
    certificate = factories.CertificateFactory.create()
    measures = [
        factories.MeasureFactory.create(
            valid_between=date_ranges.earlier,
        ),
        factories.MeasureFactory.create(
            valid_between=date_ranges.normal,
        ),
        factories.MeasureFactory.create(
            valid_between=date_ranges.later,
        ),
    ]
    for measure in measures:
        factories.MeasureConditionFactory.create(
            dependent_measure=measure,
            required_certificate=certificate,
        )
    url = reverse(
        "certificate-ui-detail-measures",
        kwargs={
            "sid": certificate.sid,
            "certificate_type__sid": certificate.certificate_type.sid,
        },
    )
    response = valid_user_client.get(f"{url}?sort_by=start_date&ordered=asc")
    page = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )
    table_measure_sids = [
        int(sid.text) for sid in page.select(".govuk-table tbody tr td:first-child")
    ]
    assert table_measure_sids == [measures[0].sid, measures[1].sid, measures[2].sid]

    response = valid_user_client.get(f"{url}?sort_by=start_date&ordered=desc")
    page = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )
    table_measure_sids = [
        int(sid.text) for sid in page.select(".govuk-table tbody tr td:first-child")
    ]
    assert table_measure_sids == [measures[2].sid, measures[1].sid, measures[0].sid]


def test_certificate_detail_version_control_view(valid_user_client):
    """Test that `CertificateDetailVersionControl` view returns 200 and renders
    table content and other tabs."""
    certificate = factories.CertificateFactory.create()
    certificate.new_version(certificate.transaction.workbasket)

    url_kwargs = {
        "sid": certificate.sid,
        "certificate_type__sid": certificate.certificate_type.sid,
    }

    details_tab_url = reverse("certificate-ui-detail", kwargs=url_kwargs)
    version_control_tab_url = reverse(
        "certificate-ui-detail-version-control",
        kwargs=url_kwargs,
    )
    measures_tab_url = reverse("certificate-ui-detail-measures", kwargs=url_kwargs)
    descriptions_tab_url = reverse(
        "certificate-ui-detail-descriptions",
        kwargs=url_kwargs,
    )
    expected_tabs = {
        "Details": details_tab_url,
        "Descriptions": descriptions_tab_url,
        "Measures": measures_tab_url,
        "Version control": version_control_tab_url,
    }

    response = valid_user_client.get(version_control_tab_url)
    assert response.status_code == 200
    page = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )

    tabs = {tab.text: tab.attrs["href"] for tab in page.select(".govuk-tabs__tab")}
    assert tabs == expected_tabs

    table_rows = page.select("table > tbody > tr")
    assert len(table_rows) == 2

    update_types = {
        update.text for update in page.select("table > tbody > tr > td:first-child")
    }
    assert update_types == {"Create", "Update"}
