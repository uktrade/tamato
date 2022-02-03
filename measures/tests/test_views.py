import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from common.tests import factories
from common.tests.util import assert_model_view_renders
from common.tests.util import get_class_based_view_urls_matching_url
from common.tests.util import raises_if
from common.tests.util import view_is_subclass
from common.tests.util import view_urlpattern_ids
from common.views import TamatoListView
from common.views import TrackedModelDetailMixin
from measures.validators import validate_duties
from measures.views import MeasureFootnotesUpdate
from measures.views import MeasureList

pytestmark = pytest.mark.django_db


def test_measure_footnotes_update_get_delete_key():
    footnote_key = "form-0-footnote"
    expected = "form-0-DELETE"
    delete_key = MeasureFootnotesUpdate().get_delete_key(footnote_key)

    assert delete_key == expected


def test_measure_footnotes_update_post_remove(client, valid_user):
    measure = factories.MeasureFactory.create()
    footnote = factories.FootnoteAssociationMeasureFactory.create(
        footnoted_measure=measure,
    ).associated_footnote
    url = reverse("measure-ui-edit-footnotes", kwargs={"sid": measure.sid})
    post_data = {"remove": footnote.pk}
    client.force_login(valid_user)
    session = client.session
    session.update({f"instance_footnotes_{measure.sid}": [footnote.pk]})
    session.save()

    client.post(url, data=post_data)

    assert client.session[f"instance_footnotes_{measure.sid}"] == []


def test_measure_footnotes_update_post_without_remove(client, valid_user):
    measure = factories.MeasureFactory.create()
    footnote_1 = factories.FootnoteAssociationMeasureFactory.create(
        footnoted_measure=measure,
    ).associated_footnote
    footnote_2 = factories.FootnoteAssociationMeasureFactory.create(
        footnoted_measure=measure,
    ).associated_footnote
    url = reverse("measure-ui-edit-footnotes", kwargs={"sid": measure.sid})
    post_data = {"form-1-footnote": footnote_1.pk, "form-2-footnote": footnote_2.pk}
    client.force_login(valid_user)

    client.post(url, data=post_data)

    assert client.session[f"formset_initial_{measure.sid}"] == [
        {"footnote": str(footnote_1.pk)},
        {"footnote": str(footnote_2.pk)},
    ]


def test_measure_footnotes_update_post_without_remove_ignores_delete_keys(
    client,
    valid_user,
):
    measure = factories.MeasureFactory.create()
    footnote_1 = factories.FootnoteAssociationMeasureFactory.create(
        footnoted_measure=measure,
    ).associated_footnote
    footnote_2 = factories.FootnoteAssociationMeasureFactory.create(
        footnoted_measure=measure,
    ).associated_footnote
    url = reverse("measure-ui-edit-footnotes", kwargs={"sid": measure.sid})
    post_data = {
        "form-1-footnote": footnote_1.pk,
        "form-2-footnote": footnote_2.pk,
        "form-2-DELETE": "",
    }
    client.force_login(valid_user)

    client.post(url, data=post_data)

    assert client.session[f"formset_initial_{measure.sid}"] == [
        {"footnote": str(footnote_1.pk)},
    ]


def test_measure_delete(use_delete_form):
    use_delete_form(factories.MeasureFactory())


@pytest.mark.parametrize(
    ("view", "url_pattern"),
    get_class_based_view_urls_matching_url(
        "measures/",
        view_is_subclass(TrackedModelDetailMixin),
    ),
    ids=view_urlpattern_ids,
)
def test_measure_detail_views(view, url_pattern, valid_user_client):
    """Verify that measure detail views are under the url measures/ and don't
    return an error."""
    assert_model_view_renders(view, url_pattern, valid_user_client)


@pytest.mark.parametrize(
    ("view", "url_pattern"),
    get_class_based_view_urls_matching_url(
        "measures/",
        view_is_subclass(TamatoListView),
        assert_contains_view_classes=[MeasureList],
    ),
    ids=view_urlpattern_ids,
)
def test_measure_list_view(view, url_pattern, valid_user_client):
    """Verify that measure list view is under the url measures/ and doesn't
    return an error."""
    assert_model_view_renders(view, url_pattern, valid_user_client)


@pytest.mark.parametrize(
    ("duties", "error_expected"),
    [
        ("33 GBP/100kg", False),
        ("33 GBP/100kge", True),
    ],
)
def test_duties_validator(
    duties,
    error_expected,
    date_ranges,
    duty_sentence_parser,
):
    # duty_sentence_parser populates data needed by the DutySentenceParser
    # removing it will cause the test to fail.
    with raises_if(ValidationError, error_expected):
        validate_duties(duties, date_ranges.normal)
