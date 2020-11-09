import pytest
from pytest import raises
from pytest_django.asserts import assertQuerysetEqual

from common.tests.factories import (
    ApprovedWorkBasketFactory,
    RegulationGroupFactory,
    RegulationFactory,
    FootnoteTypeFactory,
)
from footnotes.models import FootnoteType
from regulations.models import Regulation, Group
from workbaskets.models import WorkBasket

pytestmark = pytest.mark.django_db


def test_ordering_of_workbasket_items(approved_workbasket):
    """
    By default Workbasket.tracked_models is unsorted, verify
    calling prefetch_ordered_tracked_models sorts items
    by ascending record_code, subrecord_code.
    """
    # Add items to workbasket with record codes that are not sorted
    # Note:  regulation.Regulation implicitly creates a regulation.Group
    RegulationFactory.create(workbasket=approved_workbasket)
    FootnoteTypeFactory.create(workbasket=approved_workbasket)

    unsorted_items = approved_workbasket.tracked_models.all()
    # Assert types as a sanity check.
    assertQuerysetEqual(
        unsorted_items,
        (Regulation, Group, FootnoteType),
        transform=lambda o: o.__class__,
        ordered=False,
    )

    sorted_items = (
        WorkBasket.objects.prefetch_ordered_tracked_models()
        .get(id=approved_workbasket.id)
        .tracked_models.all()
    )

    with raises(AssertionError):
        # Verify initial items are unsorted otherwise the test will never fail.
        assertQuerysetEqual(sorted_items, unsorted_items, transform=lambda o: o)

    assertQuerysetEqual(
        sorted_items,
        sorted(unsorted_items, key=lambda o: (o.record_code, o.subrecord_code)),
        transform=lambda o: o,
        msg="Query did not sort items by record_code, subrecord_code.",
    )
