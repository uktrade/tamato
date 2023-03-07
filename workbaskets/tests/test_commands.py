from io import StringIO

import pytest
from django.core.management import call_command

from checks.checks import INTERNAL_ERROR_MESSAGE
from checks.tests.factories import TrackedModelCheckFactory
from common.tests.factories import WorkBasketFactory

pytestmark = pytest.mark.django_db


def test_override_check_success():
    model_check = TrackedModelCheckFactory.create(
        successful=False,
        message=INTERNAL_ERROR_MESSAGE,
    )
    workbasket = model_check.transaction_check.transaction.workbasket

    out = StringIO()
    call_command(
        "override_check",
        f"{workbasket.pk}",
        f"{model_check.pk}",
        stdout=out,
    )

    assert "both set as successful" in out.getvalue()


def test_override_check_workbasket_mismatch():
    model_check = TrackedModelCheckFactory.create(
        successful=False,
        message=INTERNAL_ERROR_MESSAGE,
    )
    mismatching_workbasket = WorkBasketFactory.create()

    out = StringIO()
    with pytest.raises(SystemExit):
        call_command(
            "override_check",
            f"{mismatching_workbasket.pk}",
            f"{model_check.pk}",
            stdout=out,
        )

    assert (
        f"Model check {model_check.pk} is not associated with workbasket"
        in out.getvalue()
    )


def test_override_check_invalid_error():
    model_check = TrackedModelCheckFactory.create(
        successful=False,
    )
    workbasket = model_check.transaction_check.transaction.workbasket

    out = StringIO()
    with pytest.raises(SystemExit):
        call_command(
            "override_check",
            f"{workbasket.pk}",
            f"{model_check.pk}",
            stdout=out,
        )

    assert (
        f"Model check {model_check.id} appears to be a valid error. " in out.getvalue()
    )


def test_override_check_tranx_check_not_completed():
    model_check = TrackedModelCheckFactory.create(
        successful=False,
        message=INTERNAL_ERROR_MESSAGE,
    )
    tranx_check = model_check.transaction_check
    tranx_check.completed = False
    tranx_check.successful = None
    tranx_check.save()
    workbasket = tranx_check.transaction.workbasket

    out = StringIO()
    call_command(
        "override_check",
        f"{workbasket.pk}",
        f"{model_check.pk}",
        stdout=out,
    )

    assert (
        f"Related transaction check, {tranx_check.pk}, has not completed "
        in out.getvalue()
    )
