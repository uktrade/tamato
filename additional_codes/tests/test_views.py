import datetime

import factory
import pytest
from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError
from django.urls import reverse

from additional_codes.models import AdditionalCode
from additional_codes.models import AdditionalCodeDescription
from additional_codes.views import AdditionalCodeList
from common.models import Transaction
from common.models.utils import override_current_transaction
from common.tests import factories
from common.tests.util import assert_model_view_renders
from common.tests.util import assert_read_only_model_view_returns_list
from common.tests.util import date_post_data
from common.tests.util import get_class_based_view_urls_matching_url
from common.tests.util import raises_if
from common.tests.util import validity_period_post_data
from common.tests.util import view_is_subclass
from common.tests.util import view_urlpattern_ids
from common.validators import UpdateType
from common.views.base import TamatoListView
from common.views.mixins import TrackedModelDetailMixin

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("new_data", "expected_valid"),
    (
        (lambda data: {}, False),
        (
            lambda data: {
                "description": "Test description",
                "code": "002",
                "valid_between": validity_period_post_data(
                    datetime.date.today(),
                    datetime.date.today() + relativedelta(months=+1),
                ),
                **date_post_data("start_date", datetime.date.today()),
                **factory.build(
                    dict,
                    type=factories.AdditionalCodeTypeFactory.create().pk,
                    FACTORY_CLASS=factories.AdditionalCodeFactory,
                ),
            },
            True,
        ),
    ),
)
def test_additional_code_create_form(use_create_form, new_data, expected_valid):
    with raises_if(ValidationError, not expected_valid):
        use_create_form(AdditionalCode, new_data)


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
def test_additional_code_edit_views(
    data_changes,
    expected_valid,
    update_type,
    use_edit_view,
    workbasket,
    published_additional_code_type,
):
    """Tests that additional code edit views (for update types CREATE and
    UPDATE) allows saving a valid form from an existing instance and that an
    invalid form fails validation as expected."""

    additional_code = factories.AdditionalCodeFactory.create(
        update_type=update_type,
        type=published_additional_code_type,
        transaction=workbasket.new_transaction(),
    )
    with raises_if(ValidationError, not expected_valid):
        use_edit_view(additional_code, data_changes)


def test_additional_code_delete_form(use_delete_form):
    use_delete_form(factories.AdditionalCodeFactory())


def test_additional_code_description_delete_form(use_delete_form):
    additional_code = factories.AdditionalCodeFactory()
    (
        description1,
        description2,
    ) = factories.AdditionalCodeDescriptionFactory.create_batch(
        2,
        described_additionalcode=additional_code,
    )
    use_delete_form(description1)
    try:
        use_delete_form(description2)
    except ValidationError as e:
        assert (
            "This description cannot be deleted because at least one description record is mandatory."
            in e.message
        )


@pytest.mark.parametrize(
    ("view", "url_pattern"),
    get_class_based_view_urls_matching_url(
        "additional_codes/",
        view_is_subclass(TrackedModelDetailMixin),
    ),
    ids=view_urlpattern_ids,
)
def test_additional_codes_detail_views(
    view,
    url_pattern,
    valid_user_client,
    session_request_with_workbasket,
):
    """Verify that additional code detail views are under the url
    additional_codes/ and don't return an error."""
    model_overrides = {
        "additional_codes.views.AdditionalCodeDescriptionCreate": AdditionalCode,
    }

    assert_model_view_renders(view, url_pattern, valid_user_client, model_overrides)


@pytest.mark.parametrize(
    ("view", "url_pattern"),
    get_class_based_view_urls_matching_url(
        "additional_codes/",
        view_is_subclass(TamatoListView),
        assert_contains_view_classes=[AdditionalCodeList],
    ),
    ids=view_urlpattern_ids,
)
def test_additional_codes_list_view(view, url_pattern, valid_user_client):
    """Verify that additional code list view is under the url additional_codes/
    and doesn't return an error."""
    assert_model_view_renders(view, url_pattern, valid_user_client)


def test_additional_codes_api_list_view(valid_user_client, date_ranges):
    selected_type = factories.AdditionalCodeTypeFactory.create()
    expected_results = [
        factories.AdditionalCodeFactory.create(
            valid_between=date_ranges.normal,
            type=selected_type,
        ),
        factories.AdditionalCodeFactory.create(
            valid_between=date_ranges.earlier,
            type=selected_type,
        ),
    ]
    assert_read_only_model_view_returns_list(
        "additionalcode",
        "value",
        "pk",
        expected_results,
        valid_user_client,
    )


def test_additional_code_type_api_list_view(valid_user_client):
    expected_results = [
        factories.AdditionalCodeTypeFactory.create(),
    ]
    assert_read_only_model_view_returns_list(
        "additionalcodetype",
        "sid",
        "sid",
        expected_results,
        valid_user_client,
    )


def test_additional_code_details_list_current_measures(
    valid_user_client,
    date_ranges,
):
    additional_code = factories.AdditionalCodeFactory()
    old_measures = factories.MeasureFactory.create_batch(
        5,
        valid_between=date_ranges.adjacent_earlier_big,
        additional_code=additional_code,
    )
    current_measures = factories.MeasureFactory.create_batch(
        4,
        valid_between=date_ranges.normal,
        additional_code=additional_code,
    )
    url = reverse("additional_code-ui-detail", kwargs={"sid": additional_code.sid})
    response = valid_user_client.get(url)
    soup = BeautifulSoup(response.content.decode(response.charset), "html.parser")
    num_measures = len(
        soup.select("#measures table tbody > tr > td:first-child"),
    )
    assert num_measures == 4


def test_additional_code_details_list_no_measures(valid_user_client):
    additional_code = factories.AdditionalCodeFactory()
    url = reverse("additional_code-ui-detail", kwargs={"sid": additional_code.sid})
    response = valid_user_client.get(url)
    soup = BeautifulSoup(response.content.decode(response.charset), "html.parser")
    num_measures = len(
        soup.select("#measures table tbody > tr > td:first-child"),
    )
    assert num_measures == 0


def test_additional_code_description_create(client_with_current_workbasket):
    """Tests that `AdditionalCodeDescriptionCreate` view returns 200 and creates
    a description for the current version of an additional code."""
    additional_code = factories.AdditionalCodeFactory.create()
    new_version = additional_code.new_version(
        workbasket=additional_code.transaction.workbasket,
    )
    assert not AdditionalCodeDescription.objects.exists()

    url = reverse(
        "additional_code-ui-description-create",
        kwargs={"sid": new_version.sid},
    )
    data = {
        "description": "new test description",
        "described_additionalcode": new_version.pk,
        "validity_start_0": 1,
        "validity_start_1": 1,
        "validity_start_2": 2023,
    }

    with override_current_transaction(Transaction.objects.last()):
        get_response = client_with_current_workbasket.get(url)
        assert get_response.status_code == 200

        post_response = client_with_current_workbasket.post(url, data)
        assert post_response.status_code == 302

    assert AdditionalCodeDescription.objects.filter(
        described_additionalcode__sid=new_version.sid,
    ).exists()
