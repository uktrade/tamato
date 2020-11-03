import pytest
from pytest import raises
from pytest_django.asserts import assertQuerysetEqual

from common.tests.factories import (
    ApprovedWorkBasketFactory,
    RegulationGroupFactory,
    RegulationFactory,
    FootnoteTypeFactory,
)
from workbaskets.models import WorkBasket

pytestmark = pytest.mark.django_db


def test_ordering_of_workbasket_items(approved_workbasket):
    """
    By default Workbasket.tracked_models is unsorted, verify
    that calling prefetch_ordered_tracked_models sorts them
    by record_code, subrecord_code.
    """
    # Add items to workbasket with record codes that are not sorted:
    regulation_group = RegulationGroupFactory()
    RegulationFactory(workbasket=approved_workbasket, regulation_group=regulation_group)
    FootnoteTypeFactory(workbasket=approved_workbasket)

    unsorted_items = approved_workbasket.tracked_models.all()
    sorted_items = (
        WorkBasket.objects.prefetch_ordered_tracked_models()
        .get(id=approved_workbasket.id)
        .tracked_models.all()
    )

    with raises(AssertionError):
        # This will only happen if this test or (more likely)
        # the classes, it references are edited.
        assertQuerysetEqual(sorted_items, unsorted_items, transform=lambda o: o)

    assertQuerysetEqual(
        sorted_items,
        sorted(unsorted_items, key=lambda o: (o.record_code, o.subrecord_code)),
        transform=lambda o: o,
    )
