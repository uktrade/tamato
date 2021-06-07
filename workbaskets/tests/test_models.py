from contextlib import nullcontext as does_not_raise
from unittest import mock

import pytest
from django_fsm import TransitionNotAllowed

from common.models import TrackedModel
from common.tests import factories
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
    "start_status,transition,target_status,expect_error,expect_upload",
    [
        # Submission
        (
            WorkflowStatus.NEW_IN_PROGRESS,
            "submit_for_approval",
            WorkflowStatus.AWAITING_APPROVAL,
            does_not_raise(),
            False,
        ),
        (
            WorkflowStatus.EDITING,
            "submit_for_approval",
            WorkflowStatus.AWAITING_APPROVAL,
            does_not_raise(),
            False,
        ),
        (
            WorkflowStatus.APPROVAL_REJECTED,
            "submit_for_approval",
            WorkflowStatus.AWAITING_APPROVAL,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.READY_FOR_EXPORT,
            "submit_for_approval",
            WorkflowStatus.AWAITING_APPROVAL,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_CREATE_NEW,
            "submit_for_approval",
            WorkflowStatus.AWAITING_APPROVAL,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_EDIT,
            "submit_for_approval",
            WorkflowStatus.AWAITING_APPROVAL,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_OVERWRITE,
            "submit_for_approval",
            WorkflowStatus.AWAITING_APPROVAL,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_DELETE,
            "submit_for_approval",
            WorkflowStatus.AWAITING_APPROVAL,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.SENT_TO_CDS,
            "submit_for_approval",
            WorkflowStatus.AWAITING_APPROVAL,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.SENT_TO_CDS_DELETE,
            "submit_for_approval",
            WorkflowStatus.AWAITING_APPROVAL,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.PUBLISHED,
            "submit_for_approval",
            WorkflowStatus.AWAITING_APPROVAL,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.CDS_ERROR,
            "submit_for_approval",
            WorkflowStatus.AWAITING_APPROVAL,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        # Withdraw
        (
            WorkflowStatus.NEW_IN_PROGRESS,
            "withdraw",
            WorkflowStatus.EDITING,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.AWAITING_APPROVAL,
            "withdraw",
            WorkflowStatus.EDITING,
            does_not_raise(),
            False,
        ),
        (
            WorkflowStatus.APPROVAL_REJECTED,
            "withdraw",
            WorkflowStatus.EDITING,
            does_not_raise(),
            False,
        ),
        (
            WorkflowStatus.READY_FOR_EXPORT,
            "withdraw",
            WorkflowStatus.EDITING,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_CREATE_NEW,
            "withdraw",
            WorkflowStatus.EDITING,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_EDIT,
            "withdraw",
            WorkflowStatus.EDITING,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_OVERWRITE,
            "withdraw",
            WorkflowStatus.EDITING,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_DELETE,
            "withdraw",
            WorkflowStatus.EDITING,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.SENT_TO_CDS,
            "withdraw",
            WorkflowStatus.EDITING,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.SENT_TO_CDS_DELETE,
            "withdraw",
            WorkflowStatus.EDITING,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.PUBLISHED,
            "withdraw",
            WorkflowStatus.EDITING,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.CDS_ERROR,
            "withdraw",
            WorkflowStatus.EDITING,
            does_not_raise(),
            False,
        ),
        # Rejection
        (
            WorkflowStatus.NEW_IN_PROGRESS,
            "reject",
            WorkflowStatus.APPROVAL_REJECTED,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.EDITING,
            "reject",
            WorkflowStatus.APPROVAL_REJECTED,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.AWAITING_APPROVAL,
            "reject",
            WorkflowStatus.APPROVAL_REJECTED,
            does_not_raise(),
            False,
        ),
        (
            WorkflowStatus.READY_FOR_EXPORT,
            "reject",
            WorkflowStatus.APPROVAL_REJECTED,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_CREATE_NEW,
            "reject",
            WorkflowStatus.APPROVAL_REJECTED,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_EDIT,
            "reject",
            WorkflowStatus.APPROVAL_REJECTED,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_OVERWRITE,
            "reject",
            WorkflowStatus.APPROVAL_REJECTED,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_DELETE,
            "reject",
            WorkflowStatus.APPROVAL_REJECTED,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.SENT_TO_CDS,
            "reject",
            WorkflowStatus.APPROVAL_REJECTED,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.SENT_TO_CDS_DELETE,
            "reject",
            WorkflowStatus.APPROVAL_REJECTED,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.PUBLISHED,
            "reject",
            WorkflowStatus.APPROVAL_REJECTED,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.CDS_ERROR,
            "reject",
            WorkflowStatus.APPROVAL_REJECTED,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        # Approval
        (
            WorkflowStatus.NEW_IN_PROGRESS,
            "approve",
            WorkflowStatus.READY_FOR_EXPORT,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.EDITING,
            "approve",
            WorkflowStatus.READY_FOR_EXPORT,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.AWAITING_APPROVAL,
            "approve",
            WorkflowStatus.READY_FOR_EXPORT,
            does_not_raise(),
            True,
        ),
        (
            WorkflowStatus.APPROVAL_REJECTED,
            "approve",
            WorkflowStatus.READY_FOR_EXPORT,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_CREATE_NEW,
            "approve",
            WorkflowStatus.READY_FOR_EXPORT,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_EDIT,
            "approve",
            WorkflowStatus.READY_FOR_EXPORT,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_OVERWRITE,
            "approve",
            WorkflowStatus.READY_FOR_EXPORT,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_DELETE,
            "approve",
            WorkflowStatus.READY_FOR_EXPORT,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.SENT_TO_CDS,
            "approve",
            WorkflowStatus.READY_FOR_EXPORT,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.SENT_TO_CDS_DELETE,
            "approve",
            WorkflowStatus.READY_FOR_EXPORT,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.PUBLISHED,
            "approve",
            WorkflowStatus.READY_FOR_EXPORT,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.CDS_ERROR,
            "approve",
            WorkflowStatus.READY_FOR_EXPORT,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        # Export
        (
            WorkflowStatus.NEW_IN_PROGRESS,
            "export_to_cds",
            WorkflowStatus.SENT_TO_CDS,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.EDITING,
            "export_to_cds",
            WorkflowStatus.SENT_TO_CDS,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.AWAITING_APPROVAL,
            "export_to_cds",
            WorkflowStatus.SENT_TO_CDS,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.APPROVAL_REJECTED,
            "export_to_cds",
            WorkflowStatus.SENT_TO_CDS,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.READY_FOR_EXPORT,
            "export_to_cds",
            WorkflowStatus.SENT_TO_CDS,
            does_not_raise(),
            False,
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_CREATE_NEW,
            "export_to_cds",
            WorkflowStatus.SENT_TO_CDS,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_EDIT,
            "export_to_cds",
            WorkflowStatus.SENT_TO_CDS,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_OVERWRITE,
            "export_to_cds",
            WorkflowStatus.SENT_TO_CDS,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_DELETE,
            "export_to_cds",
            WorkflowStatus.SENT_TO_CDS,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.SENT_TO_CDS_DELETE,
            "export_to_cds",
            WorkflowStatus.SENT_TO_CDS,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.PUBLISHED,
            "export_to_cds",
            WorkflowStatus.SENT_TO_CDS,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.CDS_ERROR,
            "export_to_cds",
            WorkflowStatus.SENT_TO_CDS,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        # Confirmed
        (
            WorkflowStatus.NEW_IN_PROGRESS,
            "cds_confirmed",
            WorkflowStatus.PUBLISHED,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.EDITING,
            "cds_confirmed",
            WorkflowStatus.PUBLISHED,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.AWAITING_APPROVAL,
            "cds_confirmed",
            WorkflowStatus.PUBLISHED,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.APPROVAL_REJECTED,
            "cds_confirmed",
            WorkflowStatus.PUBLISHED,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.READY_FOR_EXPORT,
            "cds_confirmed",
            WorkflowStatus.PUBLISHED,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_CREATE_NEW,
            "cds_confirmed",
            WorkflowStatus.PUBLISHED,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_EDIT,
            "cds_confirmed",
            WorkflowStatus.PUBLISHED,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_OVERWRITE,
            "cds_confirmed",
            WorkflowStatus.PUBLISHED,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_DELETE,
            "cds_confirmed",
            WorkflowStatus.PUBLISHED,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.SENT_TO_CDS,
            "cds_confirmed",
            WorkflowStatus.PUBLISHED,
            does_not_raise(),
            False,
        ),
        (
            WorkflowStatus.SENT_TO_CDS_DELETE,
            "cds_confirmed",
            WorkflowStatus.PUBLISHED,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.CDS_ERROR,
            "cds_confirmed",
            WorkflowStatus.PUBLISHED,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        # Errored
        (
            WorkflowStatus.NEW_IN_PROGRESS,
            "cds_error",
            WorkflowStatus.CDS_ERROR,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.EDITING,
            "cds_error",
            WorkflowStatus.CDS_ERROR,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.AWAITING_APPROVAL,
            "cds_error",
            WorkflowStatus.CDS_ERROR,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.APPROVAL_REJECTED,
            "cds_error",
            WorkflowStatus.CDS_ERROR,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.READY_FOR_EXPORT,
            "cds_error",
            WorkflowStatus.CDS_ERROR,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_CREATE_NEW,
            "cds_error",
            WorkflowStatus.CDS_ERROR,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_EDIT,
            "cds_error",
            WorkflowStatus.CDS_ERROR,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_OVERWRITE,
            "cds_error",
            WorkflowStatus.CDS_ERROR,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.AWAITING_CDS_UPLOAD_DELETE,
            "cds_error",
            WorkflowStatus.CDS_ERROR,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.SENT_TO_CDS,
            "cds_error",
            WorkflowStatus.CDS_ERROR,
            does_not_raise(),
            False,
        ),
        (
            WorkflowStatus.SENT_TO_CDS_DELETE,
            "cds_error",
            WorkflowStatus.CDS_ERROR,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
        (
            WorkflowStatus.PUBLISHED,
            "cds_error",
            WorkflowStatus.CDS_ERROR,
            pytest.raises(TransitionNotAllowed),
            False,
        ),
    ],
)
def test_workbasket_submit(
    new_workbasket,
    start_status,
    transition,
    target_status,
    expect_error,
    expect_upload,
    valid_user,
):
    new_workbasket.status = start_status
    with mock.patch(
        "exporter.tasks.upload_workbaskets.delay",
    ) as mock_save:
        transition_method = getattr(new_workbasket, transition)
        with expect_error:
            if transition_method.__name__ == "approve":
                transition_method(valid_user)
            else:
                transition_method()
            assert new_workbasket.status == target_status

            if expect_upload:
                mock_save.assert_called_once_with()
            else:
                mock_save.assert_not_called()


def test_get_tracked_models(new_workbasket):
    for _ in range(2):
        factories.FootnoteFactory.create()

    assert TrackedModel.objects.count() > 2
    assert new_workbasket.tracked_models.count() == 2


def test_workbasket_accepted_updates_current_tracked_models(new_workbasket, valid_user):
    original_footnote = factories.FootnoteFactory.create()
    new_footnote = original_footnote.new_version(workbasket=new_workbasket)

    assert new_footnote.version_group.current_version.pk == original_footnote.pk

    with mock.patch(
        "exporter.tasks.upload_workbaskets.delay",
    ) as mock_save:
        new_workbasket.submit_for_approval()
        new_footnote.refresh_from_db()
        assert new_footnote.version_group.current_version.pk == original_footnote.pk
        new_workbasket.approve(valid_user)
        new_footnote.refresh_from_db()
        assert new_footnote.version_group.current_version.pk == new_footnote.pk

        mock_save.assert_called_once_with()


def test_workbasket_errored_updates_tracked_models(new_workbasket, valid_user):
    original_footnote = factories.FootnoteFactory.create()
    new_footnote = original_footnote.new_version(workbasket=new_workbasket)

    assert new_footnote.version_group.current_version.pk == original_footnote.pk

    with mock.patch(
        "exporter.tasks.upload_workbaskets.delay",
    ) as mock_save:
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

        mock_save.assert_called_once_with()
