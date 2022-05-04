import unittest
from datetime import date
from decimal import Decimal
from typing import OrderedDict
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
from common.validators import UpdateType
from common.views import TamatoListView
from common.views import TrackedModelDetailMixin
from measures.models import Measure
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
        == f"{certificate.code}:\n        {certificate.get_description(transaction=certificate.transaction).description}"
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
    measure = Measure.objects.with_duty_sentence().first()
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
        == measure_edit_conditions_data["form-0-condition_code"]
    )
    assert (
        condition.required_certificate.pk
        == measure_edit_conditions_data["form-0-required_certificate"]
    )
    assert condition.action.pk == measure_edit_conditions_data["form-0-action"]

    components = condition.components.approved_up_to_transaction(tx).all()

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
    measure = Measure.objects.with_duty_sentence().first()
    previous_condition = measure.conditions.last()
    url = reverse("measure-ui-edit", args=(measure.sid,))
    client.force_login(valid_user)
    client.post(url, data=measure_edit_conditions_data)
    measure_edit_conditions_data["form-0-required_certificate"] = ""
    measure_edit_conditions_data["form-0-reference_price"] = "3%"
    measure_edit_conditions_data["form-0-applicable_duty"] = "10 GBP / 100 kg"
    client.post(url, data=measure_edit_conditions_data)
    tx = Transaction.objects.last()
    updated_measure = Measure.objects.approved_up_to_transaction(tx).get(
        sid=measure.sid,
    )

    assert updated_measure.conditions.approved_up_to_transaction(tx).count() == 1

    condition = updated_measure.conditions.approved_up_to_transaction(tx).first()

    assert condition != previous_condition
    assert condition.required_certificate == None
    assert condition.duty_amount == 3

    components = condition.components.approved_up_to_transaction(tx).all()

    assert components.count() == 1
    assert components.first().duty_amount == 10


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
    measure = Measure.objects.with_duty_sentence().first()
    url = reverse("measure-ui-edit", args=(measure.sid,))
    client.force_login(valid_user)
    client.post(url, data=measure_edit_conditions_data)
    measure_edit_conditions_data["FORM-0-DELETE"] = 1
    response = client.post(url, data=measure_edit_conditions_data)

    assert response.status_code == 200

    measure_edit_conditions_data["form-TOTAL_FORMS"] = 0
    measure_edit_conditions_data["form-INITIAL_FORMS"] = 0
    measure_edit_conditions_data["form-0-condition_code"] = ""
    measure_edit_conditions_data["form-0-required_certificate"] = ""
    measure_edit_conditions_data["form-0-action"] = ""
    measure_edit_conditions_data["form-0-applicable_duty"] = ""
    del measure_edit_conditions_data["FORM-0-DELETE"]

    response = client.post(url, data=measure_edit_conditions_data)

    assert response.status_code == 302

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
    measure_edit_conditions_data["form-0-reference_price"] = "3.5% + 11 GBP / 100 kg"
    measure_edit_conditions_data["form-0-applicable_duty"] = "invalid"
    measure = Measure.objects.with_duty_sentence().first()
    url = reverse("measure-ui-edit", args=(measure.sid,))
    client.force_login(valid_user)
    response = client.post(url, data=measure_edit_conditions_data)

    assert response.status_code == 200

    page = BeautifulSoup(
        response.content.decode(response.charset),
        features="lxml",
    )
    ul = page.find_all("ul", {"class": "govuk-list govuk-error-summary__list"})[0]
    a_tags = ul.findChildren("a")

    assert a_tags[0].attrs["href"] == "#form-0-applicable_duty"
    assert a_tags[0].text == "Enter a valid duty sentence."
    assert a_tags[1].attrs["href"] == "#form-0-__all__"
    assert (
        a_tags[1].text
        == "A MeasureCondition cannot be created with a compound reference price (e.g. 3.5% + 11 GBP / 100 kg)"
    )


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
                "measure_details-generating_regulation": regulation.pk,
                "measure_details-geo_area_type": "ERGA_OMNES",
                "measure_details-start_date_0": 2,
                "measure_details-start_date_1": 4,
                "measure_details-start_date_2": 2021,
            },
            "next_step": "commodities",
        },
        {
            "data": {
                "measure_create_wizard-current_step": "commodities",
                "commodities-0-commodity": commodity1.pk,
                "commodities-0-duties": "33 GBP/100kg",
                "commodities-1-commodity": commodity2.pk,
                "commodities-1-duties": "40 GBP/100kg",
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
    geo_area = factories.GeographicalAreaFactory.create()
    (
        condition_code1,
        condition_code2,
        condition_code3,
    ) = factories.MeasureConditionCodeFactory.create_batch(3)
    action1, action2, action3 = factories.MeasureActionFactory.create_batch(3)

    form_data = {
        "measure_type": measure_type,
        "generating_regulation": regulation,
        "geographical_area": geo_area,
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
    assert len(measure_data) == 2
    assert set(measures.values_list("pk", "goods_nomenclature_id")) == {
        (measure_data[0].pk, commodity1.pk),
        (measure_data[1].pk, commodity2.pk),
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
    }


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
