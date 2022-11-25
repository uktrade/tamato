import unittest
from datetime import date
from decimal import Decimal
from typing import OrderedDict
from unittest.mock import patch

import pytest
from bs4 import BeautifulSoup
from django.core.exceptions import ValidationError
from django.forms.models import model_to_dict
from django.urls import reverse

from common.models.transactions import Transaction
from common.models.utils import override_current_transaction
from common.tests import factories
from common.tests.util import assert_model_view_renders
from common.tests.util import assert_read_only_model_view_returns_list
from common.tests.util import get_class_based_view_urls_matching_url
from common.tests.util import raises_if
from common.tests.util import view_is_subclass
from common.tests.util import view_urlpattern_ids
from common.validators import UpdateType
from common.views import TamatoListView
from common.views import TrackedModelDetailMixin
from measures.business_rules import ME70
from measures.models import FootnoteAssociationMeasure
from measures.models import Measure
from measures.models import MeasureCondition
from measures.models import MeasureConditionComponent
from measures.models import MeasureExcludedGeographicalArea
from measures.validators import validate_duties
from measures.views import MeasureCreateWizard
from measures.views import MeasureFootnotesUpdate
from measures.views import MeasureList
from measures.views import MeasureUpdate
from measures.wizard import MeasureCreateSessionStorage
from workbaskets.models import WorkBasket

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


def test_multiple_measure_delete_functionality(client, valid_user, session_workbasket):
    """Tests that MeasureMultipleDelete view's Post function takes a list of
    measures, and sets their update type to delete, clearing the session once
    completed."""
    measure_1 = factories.MeasureFactory.create()
    measure_2 = factories.MeasureFactory.create()
    measure_3 = factories.MeasureFactory.create()

    url = reverse("measure-ui-delete-multiple")
    client.force_login(valid_user)
    session = client.session
    session["workbasket"] = {
        "id": session_workbasket.pk,
        "status": session_workbasket.status,
        "title": session_workbasket.title,
        "DELETE_MEASURE_SELECTIONS": {
            measure_1.pk: True,
            measure_2.pk: True,
            measure_3.pk: True,
        },
    }
    post_data = {"action": "delete"}
    response = client.post(url, data=post_data)

    workbasket_measures = Measure.objects.filter(
        trackedmodel_ptr__transaction__workbasket_id=session_workbasket.id,
    ).order_by("sid")

    # on success, the page redirects to the list page
    assert response.status_code == 302
    assert client.session["DELETE_MEASURE_SELECTIONS"] == {}
    for measure in workbasket_measures:
        # check that the update type is delete which is 2
        assert measure.update_type == 2


def test_multiple_measure_delete_template(client, valid_user, session_workbasket):
    """Test that valid user receives a 200 on GET for MultipleMeasureDelete and
    correct measures display in html table."""
    # Make a bunch of measures
    measure_1 = factories.MeasureFactory.create()
    measure_2 = factories.MeasureFactory.create()
    measure_3 = factories.MeasureFactory.create()
    measure_4 = factories.MeasureFactory.create()
    measure_5 = factories.MeasureFactory.create()

    url = reverse("measure-ui-delete-multiple")
    client.force_login(valid_user)
    session = client.session
    session["workbasket"] = {
        "id": session_workbasket.pk,
        "status": session_workbasket.status,
        "title": session_workbasket.title,
    }
    # Add some of those measures to the session to replicate them being selected on list page.
    session.update(
        {
            "DELETE_MEASURE_SELECTIONS": {
                measure_1.pk: True,
                measure_2.pk: True,
                measure_3.pk: True,
            },
        },
    )
    session.save()
    url = reverse("measure-ui-delete-multiple")
    response = client.get(url)

    assert response.status_code == 200

    soup = BeautifulSoup(str(response.content), "html.parser")

    # grab the whole measure objects for our pk's we've got in the session, so we can compare attributes.
    selected_measures = Measure.objects.filter(
        pk__in=[key for key in session["DELETE_MEASURE_SELECTIONS"].items()],
    )

    # Get the measure ids that are being shown in the table in the template.
    measure_ids_in_table = [e.text for e in soup.select("table tr td:first-child")]

    # Get the sids for the measures we selected, as these are what are shown in the template.
    selected_measures_ids = [str(measure.sid) for measure in selected_measures]

    assert measure_ids_in_table == selected_measures_ids
    assert set(measure_ids_in_table).difference([measure_4.sid, measure_5.sid])

    # 4th column is start date
    start_dates_in_table = {e.text for e in soup.select("table tr td:nth-child(4)")}
    measure_start_dates = {
        f"{m.valid_between.lower:%d %b %Y}" for m in selected_measures
    }
    assert not measure_start_dates.difference(start_dates_in_table)

    # 5th column is end date
    end_dates_in_table = {e.text for e in soup.select("table tr td:nth-child(5)")}
    measure_end_dates = {
        f"{m.effective_end_date:%d %b %Y}"
        for m in selected_measures
        if m.effective_end_date
    }
    assert not measure_end_dates.difference(end_dates_in_table)


@pytest.mark.parametrize(
    ("view", "url_pattern"),
    get_class_based_view_urls_matching_url(
        "measures/",
        view_is_subclass(TrackedModelDetailMixin),
    ),
    ids=view_urlpattern_ids,
)
def test_measure_detail_views(
    view,
    url_pattern,
    valid_user_client,
    session_with_workbasket,
):
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

    # ignore everything above the first condition row
    cells = page.select("#conditions table > tbody > tr:first-child > td")
    certificate = certificate_condition.required_certificate

    assert cells[0].text == str(certificate_condition.sid)
    with override_current_transaction(certificate.transaction):
        assert (
            cells[1].text
            == f"{certificate.code}:\n        {certificate.get_description().description}"
        )
    assert cells[2].text == certificate_condition.action.description
    assert cells[3].text == "-"

    cells = page.select("#conditions table > tbody > tr:nth-child(2) > td")

    assert cells[0].text == str(amount_condition.sid)
    assert (
        cells[1].text
        == f"\n    1000.000\n        {amount_condition.monetary_unit.code}"
    )
    rows = page.select("#conditions table > tbody > tr")
    assert len(rows) == 2


def test_measure_detail_no_conditions(client, valid_user):
    measure = factories.MeasureFactory.create()
    url = reverse("measure-ui-detail", kwargs={"sid": measure.sid}) + "#conditions"
    client.force_login(valid_user)
    response = client.get(url)
    page = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )

    assert (
        page.select("#conditions .govuk-body")[0].text
        == "This measure has no conditions."
    )


def test_measure_detail_footnotes(client, valid_user):
    measure = factories.MeasureFactory.create()
    footnote1 = factories.FootnoteAssociationMeasureFactory.create(
        footnoted_measure=measure,
    ).associated_footnote
    footnote2 = factories.FootnoteAssociationMeasureFactory.create(
        footnoted_measure=measure,
    ).associated_footnote
    url = reverse("measure-ui-detail", kwargs={"sid": measure.sid}) + "#footnotes"
    client.force_login(valid_user)
    response = client.get(url)
    page = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )
    rows = page.select("#footnotes table > tbody > tr")
    assert len(rows) == 2

    first_column_links = page.select(
        "#footnotes table > tbody > tr > td:first-child > a",
    )
    assert {link.text for link in first_column_links} == {
        str(footnote1),
        str(footnote2),
    }
    assert {link.get("href") for link in first_column_links} == {
        footnote1.get_url(),
        footnote2.get_url(),
    }

    second_column = page.select("#footnotes table > tbody > tr > td:nth-child(2)")
    assert {cell.text for cell in second_column} == {
        footnote1.descriptions.first().description,
        footnote2.descriptions.first().description,
    }


def test_measure_detail_no_footnotes(client, valid_user):
    measure = factories.MeasureFactory.create()
    url = reverse("measure-ui-detail", kwargs={"sid": measure.sid}) + "#footnotes"
    client.force_login(valid_user)
    response = client.get(url)
    page = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )

    assert (
        page.select("#footnotes .govuk-body")[0].text
        == "This measure has no footnotes."
    )


def test_measure_detail_quota_order_number(client, valid_user):
    quota_order_number = factories.QuotaOrderNumberFactory.create()
    measure = factories.MeasureFactory.create(order_number=quota_order_number)
    url = reverse("measure-ui-detail", kwargs={"sid": measure.sid})
    client.force_login(valid_user)
    response = client.get(url)
    page = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )
    items = [element.text.strip() for element in page.select("#core-data dl dd")]
    assert str(quota_order_number) in items


def test_measure_detail_version_control(client, valid_user):
    measure = factories.MeasureFactory.create()
    measure.new_version(measure.transaction.workbasket)
    measure.new_version(measure.transaction.workbasket)

    url = reverse("measure-ui-detail", kwargs={"sid": measure.sid}) + "#versions"
    client.force_login(valid_user)
    response = client.get(url)
    soup = BeautifulSoup(
        response.content.decode(response.charset),
        "html.parser",
    )
    rows = soup.select("#versions table > tbody > tr")
    assert len(rows) == 3

    update_types = {
        cell.text
        for cell in soup.select("#versions table > tbody > tr > td:first-child")
    }
    assert update_types == {"Create", "Update"}


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
        assert components.first().transaction == measure.transaction


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


def test_measure_update_get_footnotes(session_with_workbasket):
    association = factories.FootnoteAssociationMeasureFactory.create()
    view = MeasureUpdate(request=session_with_workbasket)
    footnotes = view.get_footnotes(association.footnoted_measure)

    assert len(footnotes) == 1

    association.new_version(
        WorkBasket.current(session_with_workbasket),
        update_type=UpdateType.DELETE,
    )

    footnotes = view.get_footnotes(association.footnoted_measure)

    assert len(footnotes) == 0


# https://uktrade.atlassian.net/browse/TP2000-340
def test_measure_update_updates_footnote_association(measure_form, client, valid_user):
    """Tests that when updating a measure with an existing footnote the
    MeasureFootnoteAssociation linking the measure and footnote is updated to
    point at the new, updated version of the measure."""
    post_data = measure_form.data
    post_data = {k: v for k, v in post_data.items() if v is not None}
    post_data["update_type"] = 1
    assoc = factories.FootnoteAssociationMeasureFactory.create(
        footnoted_measure=measure_form.instance,
    )
    url = reverse("measure-ui-edit", args=(measure_form.instance.sid,))
    client.force_login(valid_user)
    client.post(url, data=post_data)
    new_assoc = FootnoteAssociationMeasure.objects.last()

    ME70(new_assoc.transaction).validate(new_assoc)
    assert new_assoc.update_type == UpdateType.UPDATE
    assert new_assoc.version_group == assoc.version_group


def test_measure_update_create_conditions(
    client,
    valid_user,
    measure_edit_conditions_data,
    duty_sentence_parser,
    erga_omnes,
):
    """
    Tests that measure condition and condition component objects are created for
    a measure without any pre-existing conditions, after posting to the measure
    edit endpoint.

    Also tests that related objects (certificate and condition code) are
    present.
    """
    measure = Measure.objects.first()
    url = reverse("measure-ui-edit", args=(measure.sid,))
    client.force_login(valid_user)
    client.post(url, data=measure_edit_conditions_data)
    tx = Transaction.objects.last()
    updated_measure = Measure.objects.approved_up_to_transaction(tx).get(
        sid=measure.sid,
    )

    assert updated_measure.conditions.approved_up_to_transaction(tx).count() == 1

    condition = updated_measure.conditions.approved_up_to_transaction(tx).first()

    assert (
        condition.condition_code.pk
        == measure_edit_conditions_data["measure-conditions-formset-0-condition_code"]
    )
    assert (
        condition.required_certificate.pk
        == measure_edit_conditions_data[
            "measure-conditions-formset-0-required_certificate"
        ]
    )
    assert (
        condition.action.pk
        == measure_edit_conditions_data["measure-conditions-formset-0-action"]
    )
    assert condition.update_type == UpdateType.CREATE

    components = condition.components.approved_up_to_transaction(tx).order_by(
        *MeasureConditionComponent._meta.ordering
    )

    assert components.count() == 2
    assert components.first().duty_amount == 3.5
    assert components.last().duty_amount == 11


def test_measure_update_edit_conditions(
    client,
    valid_user,
    measure_edit_conditions_data,
    duty_sentence_parser,
    erga_omnes,
):
    """
    Tests that measure condition and condition component objects are created for
    a measure with pre-existing conditions, after posting to the measure edit
    endpoint.

    Checks that previous conditions are removed and new field values are
    correct.
    """
    measure = Measure.objects.first()
    url = reverse("measure-ui-edit", args=(measure.sid,))
    client.force_login(valid_user)
    client.post(url, data=measure_edit_conditions_data)
    transaction_count = Transaction.objects.count()
    tx = Transaction.objects.last()
    measure_with_condition = Measure.objects.approved_up_to_transaction(tx).get(
        sid=measure.sid,
    )
    previous_condition = measure_with_condition.conditions.last()
    measure_edit_conditions_data[
        "measure-conditions-formset-0-required_certificate"
    ] = ""
    measure_edit_conditions_data["measure-conditions-formset-0-reference_price"] = "3%"
    measure_edit_conditions_data[
        "measure-conditions-formset-0-applicable_duty"
    ] = "10 GBP / 100 kg"
    client.post(url, data=measure_edit_conditions_data)
    tx = Transaction.objects.last()
    updated_measure = Measure.objects.approved_up_to_transaction(tx).get(
        sid=measure.sid,
    )

    # We expect one transaction for updating the measure and updating the condition, one for deleting a component and updating a component
    assert Transaction.objects.count() == transaction_count + 2
    assert updated_measure.conditions.approved_up_to_transaction(tx).count() == 1

    condition = updated_measure.conditions.approved_up_to_transaction(tx).first()

    assert condition.pk != previous_condition.pk
    assert condition.required_certificate == None
    assert condition.duty_amount == 3
    assert condition.update_type == UpdateType.UPDATE
    assert condition.sid == previous_condition.sid

    components = condition.components.approved_up_to_transaction(tx).all()

    assert components.count() == 1

    component = components.first()

    assert component.duty_amount == 10
    assert component.update_type == UpdateType.UPDATE
    assert component.transaction == condition.transaction


# The measure edit form will always show changes until we fix this bug https://uktrade.atlassian.net/browse/TP2000-247 /PS-IGNORE
# When fixed, we should uncomment and add logic to prevent updates when there are no changes to a condition

# def test_measure_update_no_conditions_changes(
#     client,
#     valid_user,
#     measure_edit_conditions_data, /PS-IGNORE
#     duty_sentence_parser,
#     erga_omnes,
# ):
#     measure = Measure.objects.first()
#     url = reverse("measure-ui-edit", args=(measure.sid,))
#     client.force_login(valid_user) /PS-IGNORE
#     client.post(url, data=measure_edit_conditions_data) /PS-IGNORE
#     tx = Transaction.objects.last()
#     measure_with_condition = Measure.objects.approved_up_to_transaction(tx).get( /PS-IGNORE
#         sid=measure.sid, /PS-IGNORE
#     )
#     previous_condition = measure_with_condition.conditions.approved_up_to_transaction(tx).first()
#     client.post(url, data=measure_edit_conditions_data) /PS-IGNORE
#     tx = Transaction.objects.last()
#     updated_measure = Measure.objects.approved_up_to_transaction(tx).get( /PS-IGNORE
#         sid=measure.sid, /PS-IGNORE
#     )
#     condition = updated_measure.conditions.approved_up_to_transaction(tx).first()

#     assert condition.pk == previous_condition.pk
#     assert condition.update_type == UpdateType.CREATE
#     assert condition.sid == previous_condition.sid /PS-IGNORE


def test_measure_update_remove_conditions(
    client,
    valid_user,
    measure_edit_conditions_data,
    duty_sentence_parser,
    erga_omnes,
):
    """
    Tests that a 200 code is returned after posting to the measure edit endpoint
    with delete field in data.

    Checks that 302 is returned after posting an empty conditions form to edit
    endpoint and that the updated measure has no currently approved conditions
    associated with it.
    """
    measure = Measure.objects.first()
    url = reverse("measure-ui-edit", args=(measure.sid,))
    client.force_login(valid_user)
    client.post(url, data=measure_edit_conditions_data)
    measure_edit_conditions_data["measure-conditions-formset-0-DELETE"] = 1
    response = client.post(url, data=measure_edit_conditions_data)

    assert response.status_code == 200

    measure_edit_conditions_data["measure-conditions-formset-TOTAL_FORMS"] = 0
    measure_edit_conditions_data["measure-conditions-formset-INITIAL_FORMS"] = 0
    measure_edit_conditions_data["measure-conditions-formset-0-condition_code"] = ""
    measure_edit_conditions_data[
        "measure-conditions-formset-0-required_certificate"
    ] = ""
    measure_edit_conditions_data["measure-conditions-formset-0-action"] = ""
    measure_edit_conditions_data["measure-conditions-formset-0-applicable_duty"] = ""
    del measure_edit_conditions_data["measure-conditions-formset-0-DELETE"]
    transaction_count = Transaction.objects.count()
    response = client.post(url, data=measure_edit_conditions_data)

    assert response.status_code == 302
    # We expect one transaction for the measure update and condition deletion
    assert Transaction.objects.count() == transaction_count + 1

    tx = Transaction.objects.last()
    updated_measure = Measure.objects.approved_up_to_transaction(tx).get(
        sid=measure.sid,
    )

    assert updated_measure.conditions.approved_up_to_transaction(tx).count() == 0


def test_measure_update_invalid_conditions(
    client,
    valid_user,
    measure_edit_conditions_data,
    duty_sentence_parser,
    erga_omnes,
):
    """Tests that html contains appropriate form validation errors after posting
    to measure edit endpoint with compound reference_price and an invalid
    applicable_duty string."""
    measure_edit_conditions_data[
        "measure-conditions-formset-0-reference_price"
    ] = "3.5% + 11 GBP / 100 kg"
    measure_edit_conditions_data[
        "measure-conditions-formset-0-applicable_duty"
    ] = "invalid"
    measure = Measure.objects.first()
    url = reverse("measure-ui-edit", args=(measure.sid,))
    client.force_login(valid_user)
    response = client.post(url, data=measure_edit_conditions_data)

    assert response.status_code == 200

    page = BeautifulSoup(
        response.content.decode(response.charset),
        features="lxml",
    )
    a_tags = page.select("ul.govuk-list.govuk-error-summary__list a")

    assert a_tags[0].attrs["href"] == "#measure-conditions-formset-0-applicable_duty"
    assert a_tags[0].text == "Enter a valid duty sentence."
    assert a_tags[1].attrs["href"] == "#measure-conditions-formset-0-__all__"
    assert (
        a_tags[1].text
        == "A MeasureCondition cannot be created with a compound reference price (e.g. 3.5% + 11 GBP / 100 kg)"
    )


def test_measure_update_group_exclusion(client, valid_user, erga_omnes):
    """
    Tests that measure edit view handles exclusion of one group from another
    group.

    We create an erga omnes measure and a group containing two areas that also
    belong to the erga omnes group. Then post to edit endpoint with this group
    as an exclusion and check that two MeasureExcludedGeographicalArea objects
    are created with the two area sids in that excluded group.
    """
    measure = factories.MeasureFactory.create(geographical_area=erga_omnes)
    geo_group = factories.GeoGroupFactory.create()
    area_1 = factories.GeographicalMembershipFactory.create(geo_group=geo_group).member
    area_2 = factories.GeographicalMembershipFactory.create(geo_group=geo_group).member
    factories.GeographicalMembershipFactory.create(geo_group=erga_omnes, member=area_1)
    factories.GeographicalMembershipFactory.create(geo_group=erga_omnes, member=area_2)
    url = reverse("measure-ui-edit", args=(measure.sid,))
    client.force_login(valid_user)
    data = model_to_dict(measure)
    data = {k: v for k, v in data.items() if v is not None}
    start_date = data["valid_between"].lower
    data.update(
        {
            "start_date_0": start_date.day,
            "start_date_1": start_date.month,
            "start_date_2": start_date.year,
            "geo_area": "ERGA_OMNES",
            "erga_omnes_exclusions_formset-__prefix__-erga_omnes_exclusion": geo_group.pk,
        },
    )

    assert not MeasureExcludedGeographicalArea.objects.approved_up_to_transaction(
        Transaction.objects.last(),
    ).exists()

    client.post(url, data=data)
    measure_area_exclusions = (
        MeasureExcludedGeographicalArea.objects.approved_up_to_transaction(
            Transaction.objects.last(),
        )
    )

    assert measure_area_exclusions.count() == 2

    area_sids = [
        sid[0]
        for sid in measure_area_exclusions.values_list(
            "excluded_geographical_area__sid",
        )
    ]

    assert area_1.sid in area_sids
    assert area_2.sid in area_sids


@pytest.mark.django_db
def test_measure_form_wizard_start(valid_user_client):
    url = reverse("measure-ui-create", kwargs={"step": "start"})
    response = valid_user_client.get(url)
    assert response.status_code == 200


@unittest.mock.patch("measures.parsers.DutySentenceParser")
def test_measure_form_wizard_finish(
    mock_duty_sentence_parser,
    valid_user_client,
    measure_type,
    regulation,
    quota_order_number,
    duty_sentence_parser,
    erga_omnes,
):
    commodity1, commodity2 = factories.GoodsNomenclatureFactory.create_batch(2)

    mock_duty_sentence_parser.return_value = duty_sentence_parser

    wizard_data = [
        {
            "data": {"measure_create_wizard-current_step": "start"},
            "next_step": "measure_details",
        },
        {
            "data": {
                "measure_create_wizard-current_step": "measure_details",
                "measure_details-measure_type": measure_type.pk,
                "measure_details-start_date_0": 2,
                "measure_details-start_date_1": 4,
                "measure_details-start_date_2": 2021,
            },
            "next_step": "regulation_id",
        },
        {
            "data": {
                "measure_create_wizard-current_step": "regulation_id",
                "regulation_id-generating_regulation": regulation.pk,
            },
            "next_step": "quota_order_number",
        },
        {
            "data": {
                "measure_create_wizard-current_step": "quota_order_number",
                "quota_order_number-order_number": quota_order_number.pk,
            },
            "next_step": "geographical_area",
        },
        {
            "data": {
                "measure_create_wizard-current_step": "geographical_area",
                "geographical_area-geo_area": "ERGA_OMNES",
                "erga_omnes_exclusions_formset-0-erga_omnes_exclusion": "",
            },
            "next_step": "commodities",
        },
        {
            "data": {
                "measure_create_wizard-current_step": "commodities",
                "measure_commodities_duties_formset-0-commodity": commodity1.pk,  # /PS-IGNORE
                "measure_commodities_duties_formset-0-duties": "33 GBP/100kg",  # /PS-IGNORE
                "measure_commodities_duties_formset-1-commodity": commodity2.pk,
                "measure_commodities_duties_formset-1-duties": "40 GBP/100kg",
            },
            "next_step": "additional_code",
        },
        {
            "data": {"measure_create_wizard-current_step": "additional_code"},
            "next_step": "conditions",
        },
        {
            "data": {"measure_create_wizard-current_step": "conditions"},
            "next_step": "footnotes",
        },
        {
            "data": {"measure_create_wizard-current_step": "footnotes"},
            "next_step": "summary",
        },
        {
            "data": {"measure_create_wizard-current_step": "summary"},
            "next_step": "complete",
        },
    ]
    for step_data in wizard_data:
        url = reverse(
            "measure-ui-create",
            kwargs={"step": step_data["data"]["measure_create_wizard-current_step"]},
        )
        response = valid_user_client.get(url)
        assert response.status_code == 200

        response = valid_user_client.post(url, step_data["data"])
        assert response.status_code == 302

        assert response.url == reverse(
            "measure-ui-create",
            kwargs={"step": step_data["next_step"]},
        )

    complete_response = valid_user_client.get(response.url)

    assert complete_response.status_code == 200


@unittest.mock.patch("workbaskets.models.WorkBasket.current")
def test_measure_form_wizard_create_measures(
    mock_workbasket,
    mock_request,
    duty_sentence_parser,
    date_ranges,
    additional_code,
    measure_type,
    measurements,
    monetary_units,
    regulation,
    commodity1,
    commodity2,
):
    """Pass data to the MeasureWizard and verify that the created Measures
    contain the expected data."""
    mock_workbasket.return_value = factories.WorkBasketFactory.create()

    commodity3 = factories.GoodsNomenclatureFactory.create()
    footnote1, footnote2 = factories.FootnoteFactory.create_batch(2)
    geo_area1 = factories.GeographicalAreaFactory.create()
    geo_area2 = factories.GeographicalAreaFactory.create()
    (
        condition_code1,
        condition_code2,
        condition_code3,
    ) = factories.MeasureConditionCodeFactory.create_batch(3)
    action1, action2, action3 = factories.MeasureActionFactory.create_batch(3)

    form_data = {
        "measure_type": measure_type,
        "generating_regulation": regulation,
        "geo_area_list": [geo_area1, geo_area2],
        "order_number": None,
        "valid_between": date_ranges.normal,
        "formset-commodities": [
            {"commodity": commodity1, "duties": "33 GBP/100kg", "DELETE": False},
            {"commodity": commodity2, "duties": "40 GBP/100kg", "DELETE": False},
            {"commodity": commodity3, "duties": "2 GBP/100kg", "DELETE": True},
        ],
        "additional_code": None,
        "formset-conditions": [
            {
                "condition_code": condition_code1,
                "duty_amount": 4.000,
                "condition_measurement": measurements[("DTN", None)],
                "monetary_unit": monetary_units["GBP"],
                "required_certificate": None,
                "action": action1,
                "DELETE": False,
            },
            {
                "condition_code": condition_code2,
                "duty_amount": None,
                "required_certificate": None,
                "action": action2,
                "applicable_duty": "8.80 % + 1.70 EUR / 100 kg",
                "DELETE": False,
            },
            {
                "condition_code": condition_code3,
                "duty_amount": None,
                "required_certificate": None,
                "action": action3,
                "DELETE": True,
            },
        ],
        "formset-footnotes": [
            {"footnote": footnote1, "DELETE": False},
            {"footnote": footnote2, "DELETE": True},
        ],
    }

    wizard = MeasureCreateWizard(request=mock_request)

    # Create measures returns a list of created measures
    measure_data = wizard.create_measures(form_data)
    measures = Measure.objects.filter(goods_nomenclature__in=[commodity1, commodity2])

    """
    In this implementation goods_nomenclature is a FK of Measure, so there is one measure
    for each commodity specified in formset-commodities.

    Verify that the expected measures were created.
    """
    assert len(measure_data) == 4
    assert set(
        measures.values_list("pk", "goods_nomenclature_id", "geographical_area_id"),
    ) == {
        (measure_data[0].pk, commodity1.pk, geo_area1.pk),
        (measure_data[1].pk, commodity1.pk, geo_area2.pk),
        (measure_data[2].pk, commodity2.pk, geo_area1.pk),
        (measure_data[3].pk, commodity2.pk, geo_area2.pk),
    }

    assert set(
        measures.values_list("goods_nomenclature_id", "components__duty_amount"),
    ) == {
        (commodity1.pk, Decimal("33.000")),
        (commodity2.pk, Decimal("40.000")),
    }

    assert set(measures.values_list("pk", "footnotes")) == {
        (measure_data[0].pk, footnote1.pk),
        (measure_data[1].pk, footnote1.pk),
        (measure_data[2].pk, footnote1.pk),
        (measure_data[3].pk, footnote1.pk),
    }

    # Each created measure contains the supplied condition codes where DELETE=False
    # Each component should have a 1 based 'component_sequence_number' that iterates for each condition in
    # a measure.
    assert set(
        measures.values_list(
            "pk",
            "conditions__component_sequence_number",
            "conditions__condition_code",
            "conditions__duty_amount",
            "conditions__condition_measurement",
            "conditions__monetary_unit",
        ),
    ) == {
        (
            measure_data[0].pk,
            1,
            condition_code1.pk,
            Decimal("4.000"),
            measurements[("DTN", None)].pk,
            monetary_units["GBP"].pk,
        ),
        (measure_data[0].pk, 2, condition_code2.pk, None, None, None),
        (
            measure_data[1].pk,
            1,
            condition_code1.pk,
            Decimal("4.000"),
            measurements[("DTN", None)].pk,
            monetary_units["GBP"].pk,
        ),
        (measure_data[1].pk, 2, condition_code2.pk, None, None, None),
        (
            measure_data[2].pk,
            1,
            condition_code1.pk,
            Decimal("4.000"),
            measurements[("DTN", None)].pk,
            monetary_units["GBP"].pk,
        ),
        (measure_data[2].pk, 2, condition_code2.pk, None, None, None),
        (
            measure_data[3].pk,
            1,
            condition_code1.pk,
            Decimal("4.000"),
            measurements[("DTN", None)].pk,
            monetary_units["GBP"].pk,
        ),
        (measure_data[3].pk, 2, condition_code2.pk, None, None, None),
    }

    # Verify that MeasureComponents were created for each formset-condition containing an applicable-duty
    assert set(
        measures.values_list(
            "pk",
            "conditions__components__duty_amount",
            "conditions__components__monetary_unit__code",
        ),
    ) == {
        (measure_data[0].pk, None, None),
        (measure_data[0].pk, Decimal("8.800"), None),
        (measure_data[0].pk, Decimal("1.700"), "EUR"),
        (measure_data[1].pk, None, None),
        (measure_data[1].pk, Decimal("8.800"), None),
        (measure_data[1].pk, Decimal("1.700"), "EUR"),
        (measure_data[2].pk, None, None),
        (measure_data[2].pk, Decimal("8.800"), None),
        (measure_data[2].pk, Decimal("1.700"), "EUR"),
        (measure_data[3].pk, None, None),
        (measure_data[3].pk, Decimal("8.800"), None),
        (measure_data[3].pk, Decimal("1.700"), "EUR"),
    }

    sids = measures.values_list("sid")
    conditions = MeasureCondition.objects.filter(
        dependent_measure__sid__in=sids,
    ).exclude(components__isnull=True)

    # Check that condition components are created with same transaction as their components, to avoid an ActionRequiresDuty rule violation
    # https://uktrade.atlassian.net/browse/TP2000-344
    assert set(conditions.values_list("transaction")) == set(
        conditions.values_list("components__transaction"),
    )


@pytest.mark.parametrize("step", ["commodities", "conditions"])
def test_measure_create_wizard_get_form_kwargs(
    step,
    session_request,
    measure_type,
    regulation,
    erga_omnes,
):
    details_data = {
        "measure_create_wizard-current_step": "measure_details",
        "measure_details-measure_type": [measure_type.pk],
        "measure_details-generating_regulation": [regulation.pk],
        "measure_details-geo_area_type": ["ERGA_OMNES"],
        "measure_details-start_date_0": [2],
        "measure_details-start_date_1": [4],
        "measure_details-start_date_2": [2021],
    }
    storage = MeasureCreateSessionStorage(request=session_request, prefix="")
    storage.set_step_data("measure_details", details_data)
    storage._set_current_step(step)
    wizard = MeasureCreateWizard(
        request=session_request,
        storage=storage,
        initial_dict={step: {}},
        instance_dict={"measure_details": None},
    )
    wizard.form_list = OrderedDict(wizard.form_list)
    form_kwargs = wizard.get_form_kwargs(step)

    assert "measure_start_date" in form_kwargs["form_kwargs"]
    assert form_kwargs["form_kwargs"]["measure_start_date"] == date(2021, 4, 2)


def test_measure_form_creates_exclusions(
    erga_omnes,
    session_with_workbasket,
    valid_user,
    client,
):
    excluded_country1 = factories.GeographicalAreaFactory.create()
    excluded_country2 = factories.GeographicalAreaFactory.create()
    factories.GeographicalAreaFactory.create()
    measure = factories.MeasureFactory.create(geographical_area=erga_omnes)
    data = {k: v for k, v in model_to_dict(measure).items() if v is not None}
    start_date = data["valid_between"].lower
    data.update(
        start_date_0=start_date.day,
        start_date_1=start_date.month,
        start_date_2=start_date.year,
    )
    exclusions_data = {
        "geo_area": "ERGA_OMNES",
        "erga_omnes_exclusions_formset-0-erga_omnes_exclusion": excluded_country1.pk,
        "erga_omnes_exclusions_formset-1-erga_omnes_exclusion": excluded_country2.pk,
    }
    data.update(exclusions_data)
    client.force_login(valid_user)
    url = reverse("measure-ui-edit", args=(measure.sid,))
    response = client.post(url, data)
    assert response.status_code == 302
    assert measure.exclusions.all().count() == 2
    assert not set(
        [e.excluded_geographical_area for e in measure.exclusions.all()],
    ).difference({excluded_country1, excluded_country2})


def test_measuretype_api_list_view(valid_user_client):
    expected_results = [
        factories.MeasureTypeFactory.create(
            description="1 test description",
        ),
        factories.MeasureTypeFactory.create(
            description="2 test description",
        ),
    ]

    assert_read_only_model_view_returns_list(
        "measuretype",
        "value",
        "pk",
        expected_results,
        valid_user_client,
        equals=True,
    )
