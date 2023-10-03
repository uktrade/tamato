import re
from io import StringIO

import pytest
from django.core.management import call_command

from common.tests.factories import PackagedWorkBasketFactory
from publishing.models import PackagedWorkBasket

pytestmark = pytest.mark.django_db


def test_print_queue():
    """Test that printing the queue works as expected."""

    PackagedWorkBasketFactory.create_batch(2)

    out = StringIO()
    call_command("packaging_queue", stdout=out)
    output = out.getvalue()
    matches = re.findall("@ position: ([1,2])", output)

    assert len(matches) == 2
    assert matches == ["1", "2"]


def test_reset_incorrect_positions():
    """Test that correcting invalid position attribute values on
    PackagedWorkBasket instances that are currently in the queue works as
    expected."""

    PackagedWorkBasketFactory.create_batch(2)

    # Apply incorrect position values to queued items.
    packaged_workbaskets = PackagedWorkBasket.objects.all()
    for pw in packaged_workbaskets:
        pw.position += 1
    PackagedWorkBasket.objects.bulk_update(
        packaged_workbaskets,
        ["position"],
    )

    # Check invalid positions before correcting.
    positions = list(
        PackagedWorkBasket.objects.order_by("position").values_list(
            "position",
            flat=True,
        ),
    )
    assert positions == [2, 3]

    # Reset PackagedWorkBasket positions then check correctness.
    call_command("packaging_queue", "--reset-positions")
    positions = list(
        PackagedWorkBasket.objects.order_by("position").values_list(
            "position",
            flat=True,
        ),
    )
    assert positions == [1, 2]


def test_reset_correct_positions():
    """Test that correcting valid position attribute values on
    PackagedWorkBasket instances leaves them in their correct state."""

    PackagedWorkBasketFactory.create_batch(2)

    # Check that we have valid positions before applying a reset.
    positions = list(
        PackagedWorkBasket.objects.order_by("position").values_list(
            "position",
            flat=True,
        ),
    )
    assert positions == [1, 2]

    # Check position correctness again after a reset.
    call_command("packaging_queue", "--reset-positions")
    positions = list(
        PackagedWorkBasket.objects.order_by("position").values_list(
            "position",
            flat=True,
        ),
    )
    assert positions == [1, 2]
