from contextlib import nullcontext as does_not_raise

import pytest
from django_fsm import TransitionNotAllowed

from common.models import TrackedModel
from common.tests import factories
from common.validators import UpdateType
from workbaskets.validators import WorkflowStatus

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


@pytest.mark.parametrize(
    "start_status,transition,target_status,expect_error",
    [
        # Submission
        (
            WorkflowStatus.NEW_IN_PROGRESS,
            "submit_for_approval",
            WorkflowStatus.AWAITING_APPROVAL,
            does_not_raise(),
        ),
        (
            WorkflowStatus.EDITING,
            "submit_for_approval",
            WorkflowStatus.AWAITING_APPROVAL,
            does_not_raise(),
        ),
        (
            WorkflowStatus.APPROVAL_REJECTED,
            "submit_for_approval",
            WorkflowStatus.AWAITING_APPROVAL,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.READY_FOR_EXPORT,
            "submit_for_approval",
            WorkflowStatus.AWAITING_APPROVAL,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_CREATE_NEW,
            "submit_for_approval",
            WorkflowStatus.AWAITING_APPROVAL,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_EDIT,
            "submit_for_approval",
            WorkflowStatus.AWAITING_APPROVAL,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_OVERWRITE,
            "submit_for_approval",
            WorkflowStatus.AWAITING_APPROVAL,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_DELETE,
            "submit_for_approval",
            WorkflowStatus.AWAITING_APPROVAL,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.SENT_TO_CDS,
            "submit_for_approval",
            WorkflowStatus.AWAITING_APPROVAL,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.SENT_TO_CDS_DELETE,
            "submit_for_approval",
            WorkflowStatus.AWAITING_APPROVAL,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.PUBLISHED,
            "submit_for_approval",
            WorkflowStatus.AWAITING_APPROVAL,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.CDS_ERROR,
            "submit_for_approval",
            WorkflowStatus.AWAITING_APPROVAL,
            pytest.raises(TransitionNotAllowed),
        ),
        # Withdraw
        (
            WorkflowStatus.NEW_IN_PROGRESS,
            "withdraw",
            WorkflowStatus.EDITING,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.AWAITING_APPROVAL,
            "withdraw",
            WorkflowStatus.EDITING,
            does_not_raise(),
        ),
        (
            WorkflowStatus.APPROVAL_REJECTED,
            "withdraw",
            WorkflowStatus.EDITING,
            does_not_raise(),
        ),
        (
            WorkflowStatus.READY_FOR_EXPORT,
            "withdraw",
            WorkflowStatus.EDITING,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_CREATE_NEW,
            "withdraw",
            WorkflowStatus.EDITING,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_EDIT,
            "withdraw",
            WorkflowStatus.EDITING,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_OVERWRITE,
            "withdraw",
            WorkflowStatus.EDITING,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_DELETE,
            "withdraw",
            WorkflowStatus.EDITING,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.SENT_TO_CDS,
            "withdraw",
            WorkflowStatus.EDITING,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.SENT_TO_CDS_DELETE,
            "withdraw",
            WorkflowStatus.EDITING,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.PUBLISHED,
            "withdraw",
            WorkflowStatus.EDITING,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.CDS_ERROR,
            "withdraw",
            WorkflowStatus.EDITING,
            does_not_raise(),
        ),
        # Rejection
        (
            WorkflowStatus.NEW_IN_PROGRESS,
            "reject",
            WorkflowStatus.APPROVAL_REJECTED,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.EDITING,
            "reject",
            WorkflowStatus.APPROVAL_REJECTED,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.AWAITING_APPROVAL,
            "reject",
            WorkflowStatus.APPROVAL_REJECTED,
            does_not_raise(),
        ),
        (
            WorkflowStatus.READY_FOR_EXPORT,
            "reject",
            WorkflowStatus.APPROVAL_REJECTED,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_CREATE_NEW,
            "reject",
            WorkflowStatus.APPROVAL_REJECTED,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_EDIT,
            "reject",
            WorkflowStatus.APPROVAL_REJECTED,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_OVERWRITE,
            "reject",
            WorkflowStatus.APPROVAL_REJECTED,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_DELETE,
            "reject",
            WorkflowStatus.APPROVAL_REJECTED,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.SENT_TO_CDS,
            "reject",
            WorkflowStatus.APPROVAL_REJECTED,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.SENT_TO_CDS_DELETE,
            "reject",
            WorkflowStatus.APPROVAL_REJECTED,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.PUBLISHED,
            "reject",
            WorkflowStatus.APPROVAL_REJECTED,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.CDS_ERROR,
            "reject",
            WorkflowStatus.APPROVAL_REJECTED,
            pytest.raises(TransitionNotAllowed),
        ),
        # Approval
        (
            WorkflowStatus.NEW_IN_PROGRESS,
            "approve",
            WorkflowStatus.READY_FOR_EXPORT,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.EDITING,
            "approve",
            WorkflowStatus.READY_FOR_EXPORT,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.AWAITING_APPROVAL,
            "approve",
            WorkflowStatus.READY_FOR_EXPORT,
            does_not_raise(),
        ),
        (
            WorkflowStatus.APPROVAL_REJECTED,
            "approve",
            WorkflowStatus.READY_FOR_EXPORT,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_CREATE_NEW,
            "approve",
            WorkflowStatus.READY_FOR_EXPORT,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_EDIT,
            "approve",
            WorkflowStatus.READY_FOR_EXPORT,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_OVERWRITE,
            "approve",
            WorkflowStatus.READY_FOR_EXPORT,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_DELETE,
            "approve",
            WorkflowStatus.READY_FOR_EXPORT,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.SENT_TO_CDS,
            "approve",
            WorkflowStatus.READY_FOR_EXPORT,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.SENT_TO_CDS_DELETE,
            "approve",
            WorkflowStatus.READY_FOR_EXPORT,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.PUBLISHED,
            "approve",
            WorkflowStatus.READY_FOR_EXPORT,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.CDS_ERROR,
            "approve",
            WorkflowStatus.READY_FOR_EXPORT,
            pytest.raises(TransitionNotAllowed),
        ),
        # Export
        (
            WorkflowStatus.NEW_IN_PROGRESS,
            "export_to_cds",
            WorkflowStatus.SENT_TO_CDS,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.EDITING,
            "export_to_cds",
            WorkflowStatus.SENT_TO_CDS,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.AWAITING_APPROVAL,
            "export_to_cds",
            WorkflowStatus.SENT_TO_CDS,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.APPROVAL_REJECTED,
            "export_to_cds",
            WorkflowStatus.SENT_TO_CDS,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.READY_FOR_EXPORT,
            "export_to_cds",
            WorkflowStatus.SENT_TO_CDS,
            does_not_raise(),
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_CREATE_NEW,
            "export_to_cds",
            WorkflowStatus.SENT_TO_CDS,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_EDIT,
            "export_to_cds",
            WorkflowStatus.SENT_TO_CDS,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_OVERWRITE,
            "export_to_cds",
            WorkflowStatus.SENT_TO_CDS,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_DELETE,
            "export_to_cds",
            WorkflowStatus.SENT_TO_CDS,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.SENT_TO_CDS_DELETE,
            "export_to_cds",
            WorkflowStatus.SENT_TO_CDS,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.PUBLISHED,
            "export_to_cds",
            WorkflowStatus.SENT_TO_CDS,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.CDS_ERROR,
            "export_to_cds",
            WorkflowStatus.SENT_TO_CDS,
            pytest.raises(TransitionNotAllowed),
        ),
        # Confirmed
        (
            WorkflowStatus.NEW_IN_PROGRESS,
            "cds_confirmed",
            WorkflowStatus.PUBLISHED,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.EDITING,
            "cds_confirmed",
            WorkflowStatus.PUBLISHED,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.AWAITING_APPROVAL,
            "cds_confirmed",
            WorkflowStatus.PUBLISHED,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.APPROVAL_REJECTED,
            "cds_confirmed",
            WorkflowStatus.PUBLISHED,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.READY_FOR_EXPORT,
            "cds_confirmed",
            WorkflowStatus.PUBLISHED,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_CREATE_NEW,
            "cds_confirmed",
            WorkflowStatus.PUBLISHED,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_EDIT,
            "cds_confirmed",
            WorkflowStatus.PUBLISHED,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_OVERWRITE,
            "cds_confirmed",
            WorkflowStatus.PUBLISHED,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_DELETE,
            "cds_confirmed",
            WorkflowStatus.PUBLISHED,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.SENT_TO_CDS,
            "cds_confirmed",
            WorkflowStatus.PUBLISHED,
            does_not_raise(),
        ),
        (
            WorkflowStatus.SENT_TO_CDS_DELETE,
            "cds_confirmed",
            WorkflowStatus.PUBLISHED,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.CDS_ERROR,
            "cds_confirmed",
            WorkflowStatus.PUBLISHED,
            pytest.raises(TransitionNotAllowed),
        ),
        # Errored
        (
            WorkflowStatus.NEW_IN_PROGRESS,
            "cds_error",
            WorkflowStatus.CDS_ERROR,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.EDITING,
            "cds_error",
            WorkflowStatus.CDS_ERROR,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.AWAITING_APPROVAL,
            "cds_error",
            WorkflowStatus.CDS_ERROR,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.APPROVAL_REJECTED,
            "cds_error",
            WorkflowStatus.CDS_ERROR,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.READY_FOR_EXPORT,
            "cds_error",
            WorkflowStatus.CDS_ERROR,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_CREATE_NEW,
            "cds_error",
            WorkflowStatus.CDS_ERROR,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_EDIT,
            "cds_error",
            WorkflowStatus.CDS_ERROR,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_OVERWRITE,
            "cds_error",
            WorkflowStatus.CDS_ERROR,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_DELETE,
            "cds_error",
            WorkflowStatus.CDS_ERROR,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.SENT_TO_CDS,
            "cds_error",
            WorkflowStatus.CDS_ERROR,
            does_not_raise(),
        ),
        (
            WorkflowStatus.SENT_TO_CDS_DELETE,
            "cds_error",
            WorkflowStatus.CDS_ERROR,
            pytest.raises(TransitionNotAllowed),
        ),
        (
            WorkflowStatus.PUBLISHED,
            "cds_error",
            WorkflowStatus.CDS_ERROR,
            pytest.raises(TransitionNotAllowed),
        ),
    ],
)
def test_workbasket_submit(
    new_workbasket,
    start_status,
    transition,
    target_status,
    expect_error,
    valid_user,
):
    new_workbasket.status = start_status

    transition_method = getattr(new_workbasket, transition)
    with expect_error:
        if transition_method.__name__ == "approve":
            transition_method(valid_user)
        else:
            transition_method()
        assert new_workbasket.status == target_status


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
