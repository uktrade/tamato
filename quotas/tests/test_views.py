import pytest

from common.tests import factories
from common.tests.util import assert_model_view_renders
from common.tests.util import assert_read_only_model_view_returns_list
from common.tests.util import get_class_based_view_urls_matching_url
from common.tests.util import view_is_subclass
from common.tests.util import view_urlpattern_ids
from common.views import TamatoListView
from common.views import TrackedModelDetailMixin
from quotas.views import QuotaList

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "factory",
    (factories.QuotaOrderNumberFactory,),
)
def test_quota_delete_form(factory, use_delete_form):
    use_delete_form(factory())


@pytest.mark.parametrize(
    ("view", "url_pattern"),
    get_class_based_view_urls_matching_url(
        "quotas/",
        view_is_subclass(TrackedModelDetailMixin),
    ),
    ids=view_urlpattern_ids,
)
def test_quota_detail_views(view, url_pattern, valid_user_client):
    """Verify that quota detail views are under the url quotas and don't return
    an error."""
    assert_model_view_renders(view, url_pattern, valid_user_client)


@pytest.mark.parametrize(
    ("view", "url_pattern"),
    get_class_based_view_urls_matching_url(
        "quotas/",
        view_is_subclass(TamatoListView),
        assert_contains_view_classes=[QuotaList],
    ),
    ids=view_urlpattern_ids,
)
def test_quota_list_view(view, url_pattern, valid_user_client):
    """Verify that quota list view is under the url quotas/ and doesn't return
    an error."""
    assert_model_view_renders(view, url_pattern, valid_user_client)


def test_quota_ordernumber_api_list_view(valid_user_client, date_ranges):
    expected_results = [
        factories.QuotaOrderNumberFactory.create(
            valid_between=date_ranges.normal,
        ),
        factories.QuotaOrderNumberFactory.create(
            valid_between=date_ranges.earlier,
        ),
    ]

    assert_read_only_model_view_returns_list(
        "quotaordernumber",
        "value",
        "pk",
        expected_results,
        valid_user_client,
    )


def test_quota_ordernumberorigin_api_list_view(valid_user_client, date_ranges):
    order_number = factories.QuotaOrderNumberFactory.create()
    expected_results = [
        factories.QuotaOrderNumberOriginFactory.create(
            valid_between=date_ranges.normal,
            order_number=order_number,
        ),
        factories.QuotaOrderNumberOriginFactory.create(
            valid_between=date_ranges.earlier,
            order_number=order_number,
        ),
    ]

    assert_read_only_model_view_returns_list(
        "quotaordernumberorigin",
        "sid",
        "sid",
        expected_results,
        valid_user_client,
    )


def test_quota_ordernumberoriginexclusion_api_list_view(valid_user_client):
    order_number_origin = factories.QuotaOrderNumberOriginFactory.create()
    expected_results = [
        factories.QuotaOrderNumberOriginExclusionFactory.create(
            origin=order_number_origin,
        ),
        factories.QuotaOrderNumberOriginExclusionFactory.create(
            origin=order_number_origin,
        ),
    ]

    assert_read_only_model_view_returns_list(
        "quotaordernumberoriginexclusion",
        "origin.sid",
        "origin.sid",
        expected_results,
        valid_user_client,
    )


def test_quota_definition_api_list_view(valid_user_client):
    expected_results = [factories.QuotaDefinitionFactory.create()]

    assert_read_only_model_view_returns_list(
        "quotadefinition",
        "sid",
        "sid",
        expected_results,
        valid_user_client,
    )


def test_quota_association_api_list_view(valid_user_client):
    main_quota = factories.QuotaDefinitionFactory.create()

    expected_results = [
        factories.QuotaAssociationFactory.create(
            main_quota=main_quota,
        ),
    ]

    assert_read_only_model_view_returns_list(
        "quotaassociation",
        "main_quota.sid",
        "main_quota.sid",
        expected_results,
        valid_user_client,
    )


def test_quota_suspension_api_list_view(valid_user_client):
    expected_results = [factories.QuotaSuspensionFactory.create()]

    assert_read_only_model_view_returns_list(
        "quotasuspension",
        "sid",
        "sid",
        expected_results,
        valid_user_client,
    )


def test_quota_blocking_api_list_view(valid_user_client):
    expected_results = [factories.QuotaBlockingFactory.create()]

    assert_read_only_model_view_returns_list(
        "quotablockingperiod",
        "sid",
        "sid",
        expected_results,
        valid_user_client,
    )


def test_quota_event_api_list_view(valid_user_client):
    quota_definition = factories.QuotaDefinitionFactory.create()
    expected_results = [
        factories.QuotaEventFactory.create(
            quota_definition=quota_definition,
        ),
    ]

    assert_read_only_model_view_returns_list(
        "quotaevent",
        "quota_definition.sid",
        "quota_definition.sid",
        expected_results,
        valid_user_client,
    )
