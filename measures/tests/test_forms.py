import pytest

from common.tests import factories
from common.validators import UpdateType
from workbaskets.models import WorkBasket

pytestmark = pytest.mark.django_db


def test_diff_components_update(
    session_request,
    duty_sentence_parser,
    percent_or_amount,
    measure_form,
):
    original_component = factories.MeasureComponentFactory.create(
        component_measure=measure_form.instance,
        duty_amount=9.000,
        duty_expression=percent_or_amount,
    )
    measure_form.diff_components(
        "8.000%",
        measure_form.instance,
        measure_form.instance.valid_between.lower,
    )
    components = measure_form.instance.components.approved_up_to_transaction(
        WorkBasket.objects.get(
            id=session_request.session["workbasket"].get("id"),
        ).current_transaction,
    )

    assert components.count() == 1

    new_component = components.last()

    assert new_component.update_type == UpdateType.UPDATE
    assert new_component.version_group == original_component.version_group
    assert new_component.component_measure == measure_form.instance
    assert new_component.transaction == measure_form.instance.transaction
    assert new_component.duty_amount == 8.000


def test_diff_components_create(session_request, duty_sentence_parser, measure_form):
    measure_form.diff_components(
        "8.000%",
        measure_form.instance,
        measure_form.instance.valid_between.lower,
    )
    components = measure_form.instance.components.approved_up_to_transaction(
        WorkBasket.objects.get(
            id=session_request.session["workbasket"].get("id"),
        ).current_transaction,
    )

    assert components.count() == 1

    new_component = components.last()

    assert new_component.update_type == UpdateType.CREATE
    assert new_component.component_measure == measure_form.instance
    assert new_component.transaction == measure_form.instance.transaction
    assert new_component.duty_amount == 8.000


def test_diff_components_delete(
    session_request,
    duty_sentence_parser,
    percent_or_amount,
    measure_form,
):
    factories.MeasureComponentFactory.create(
        component_measure=measure_form.instance,
        duty_amount=9.000,
        duty_expression=percent_or_amount,
    )
    measure_form.diff_components(
        "",
        measure_form.instance,
        measure_form.instance.valid_between.lower,
    )
    components = measure_form.instance.components.approved_up_to_transaction(
        WorkBasket.objects.get(
            id=session_request.session["workbasket"].get("id"),
        ).current_transaction,
    )

    assert components.count() == 0
