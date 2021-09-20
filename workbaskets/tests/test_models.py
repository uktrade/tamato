import pytest
from django_fsm import TransitionNotAllowed

from common.models import TrackedModel
from common.tests import factories
from common.validators import UpdateType

pytestmark = pytest.mark.django_db


def test_workbasket_transactions():
    workbasket = factories.WorkBasketFactory.create()
    tx1 = workbasket.new_transaction(composite_key="test1")

    with tx1:
        measure = factories.MeasureFactory.create()

    assert measure.transaction == tx1
    assert workbasket.transactions.count() == 1

    tx2 = workbasket.new_transaction(composite_key="test2")
    assert workbasket.transactions.first() == tx1

    with tx2:
        assoc = factories.FootnoteAssociationMeasureFactory.create(
            footnoted_measure=measure,
        )

    assert assoc.transaction == tx2
    assert assoc.associated_footnote.transaction == tx2
    assert workbasket.transactions.count() == 2


def test_workbasket_transition(workbasket, transition, valid_user):
    """Tests all combinations of initial workbasket status and transition,
    testing that valid transitions do not error, and invalid transitions raise
    TransitionNotAllowed."""

    transition_args = [valid_user] if transition.name == "approve" else []

    try:
        getattr(workbasket, transition.name)(*transition_args)
        assert workbasket.status == transition.target.value
    except TransitionNotAllowed:
        assert transition.name not in [
            t.name for t in workbasket.get_available_status_transitions()
        ]


def test_get_tracked_models(new_workbasket):
    for _ in range(2):
        factories.FootnoteFactory.create()

    assert TrackedModel.objects.count() > 2
    assert new_workbasket.tracked_models.count() == 2


def test_workbasket_accepted_updates_current_tracked_models(new_workbasket, valid_user):
    original_footnote = factories.FootnoteFactory.create()
    new_footnote = original_footnote.new_version(
        workbasket=new_workbasket,
        update_type=UpdateType.UPDATE,
    )

    assert new_footnote.version_group.current_version.pk == original_footnote.pk

    new_workbasket.submit_for_approval()
    new_footnote.refresh_from_db()
    assert new_footnote.version_group.current_version.pk == original_footnote.pk
    new_workbasket.approve(valid_user)
    new_footnote.refresh_from_db()
    assert new_footnote.version_group.current_version.pk == new_footnote.pk


def test_workbasket_errored_updates_tracked_models(new_workbasket, valid_user):
    original_footnote = factories.FootnoteFactory.create()
    new_footnote = original_footnote.new_version(
        workbasket=new_workbasket,
        update_type=UpdateType.UPDATE,
    )
    assert new_footnote.version_group.current_version.pk == original_footnote.pk

    new_workbasket.submit_for_approval()
    new_footnote.refresh_from_db()
    assert new_footnote.version_group.current_version.pk == original_footnote.pk
    new_workbasket.approve(valid_user)
    new_footnote.refresh_from_db()
    assert new_footnote.version_group.current_version.pk == new_footnote.pk
    new_workbasket.export_to_cds()
    new_footnote.refresh_from_db()
    assert new_footnote.version_group.current_version.pk == new_footnote.pk
    new_workbasket.cds_error()
    new_footnote.refresh_from_db()
    assert new_footnote.version_group.current_version.pk == original_footnote.pk
