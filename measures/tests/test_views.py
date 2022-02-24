from unittest.mock import patch

import pytest
from bs4 import BeautifulSoup
from django.core.exceptions import ValidationError
from django.urls import reverse

from common.models.transactions import Transaction
from common.tests import factories
from common.tests.util import assert_model_view_renders
from common.tests.util import get_class_based_view_urls_matching_url
from common.tests.util import raises_if
from common.tests.util import view_is_subclass
from common.tests.util import view_urlpattern_ids
from common.views import TamatoListView
from common.views import TrackedModelDetailMixin
from measures.models import Measure
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


def test_measure_detail_conditions(client, valid_user):
    measure = factories.MeasureFactory.create()
    condition_code = factories.MeasureConditionCodeFactory.create()
    certificate_condition = factories.MeasureConditionWithCertificateFactory.create(
        dependent_measure=measure,
        condition_code=condition_code,
        component_sequence_number=1,
    )
    amount_condition = factories.MeasureConditionFactory.create(
        dependent_measure=measure,
        duty_amount=1000.000,
        condition_code=condition_code,
        component_sequence_number=2,
    )
    url = reverse("measure-ui-detail", kwargs={"sid": measure.sid}) + "#conditions"
    client.force_login(valid_user)
    response = client.get(url)
    page = BeautifulSoup(
        response.content.decode(response.charset),
        features="lxml",
    )

    assert (
        page.find("h3").text == f"{condition_code.code}: {condition_code.description}"
    )

    rows = page.find("table").findChildren(["th", "tr"])
    # ignore everything above the first condition row
    first_row = rows[4]
    cells = first_row.findChildren(["td"])
    certificate = certificate_condition.required_certificate

    assert (
        cells[0].text
        == f"{certificate.code}:\n        {certificate.get_description().description}"
    )
    assert cells[1].text == certificate_condition.action.description
    assert cells[2].text == "-"

    second_row = rows[5]
    cells = second_row.findChildren(["td"])

    assert (
        cells[0].text
        == f"\n    1000.000\n        {amount_condition.monetary_unit.code}"
    )
    assert len(rows) == 6


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


@pytest.mark.parametrize(
    ("update_data"),
    [
        {},
        {"duty_sentence": "10.000%"},
    ],
)
def test_measure_update_duty_sentence(
    update_data,
    client,
    valid_user,
    measure_form,
    duty_sentence_parser,
):
    """
    A placeholder test until we find a way of making use_update_form compatible
    with MeasureForm.

    Generates minimal post_data from instance and verifies that the edit
    endpoint redirects successfully. Checks that latest Measure instance has the
    correct components, if duty_sentence in data.
    """
    post_data = measure_form.data
    # Remove keys with null value to avoid TypeError
    post_data = {k: v for k, v in post_data.items() if v is not None}
    post_data.update(update_data)
    post_data["update_type"] = 1
    url = reverse("measure-ui-edit", args=(measure_form.instance.sid,))
    client.force_login(valid_user)
    response = client.post(url, data=post_data)

    assert response.status_code == 302

    if update_data:
        tx = Transaction.objects.last()
        measure = Measure.objects.approved_up_to_transaction(tx).get(
            sid=measure_form.instance.sid,
        )
        components = measure.components.approved_up_to_transaction(tx).filter(
            component_measure__sid=measure_form.instance.sid,
        )

        assert components.exists()
        assert components.count() == 1
        assert components.first().duty_amount == 10.000


# https://uktrade.atlassian.net/browse/TP2000-144
@patch("measures.forms.MeasureForm.save")
def test_measure_form_save_called_on_measure_update(
    save,
    client,
    valid_user,
    measure_form,
):
    """Until work is done to make `TrackedModel` call new_version in save() we
    need to check that MeasureUpdate view explicitly calls
    MeasureForm.save(commit=False)"""
    post_data = measure_form.data
    post_data = {k: v for k, v in post_data.items() if v is not None}
    post_data["update_type"] = 1
    url = reverse("measure-ui-edit", args=(measure_form.instance.sid,))
    client.force_login(valid_user)
    client.post(url, data=post_data)

    save.assert_called_with(commit=False)
