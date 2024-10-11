from datetime import datetime
from typing import Iterable
from unittest.mock import patch

import pytest
from django.conf import settings
from django_fsm import TransitionNotAllowed

from checks.tests.factories import TransactionCheckFactory
from common.models import TrackedModel
from common.models.transactions import Transaction
from common.models.transactions import TransactionPartition
from common.tests import factories
from common.tests.factories import ApprovedTransactionFactory
from common.tests.factories import SeedFileTransactionFactory
from common.tests.factories import TransactionFactory
from common.tests.factories import WorkBasketFactory
from common.tests.util import assert_transaction_order
from common.validators import UpdateType
from tasks.models import TaskAssignee
from workbaskets import tasks
from workbaskets.models import REVISION_ONLY
from workbaskets.models import SEED_FIRST
from workbaskets.models import SEED_ONLY
from workbaskets.models import TRANSACTION_PARTITION_SCHEMES
from workbaskets.models import TransactionPartitionScheme
from workbaskets.models import TransactionPurgeException
from workbaskets.models import UserTransactionPartitionScheme
from workbaskets.models import WorkBasket
from workbaskets.models import get_partition_scheme
from workbaskets.tests.util import assert_workbasket_valid
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


@patch("exporter.tasks.upload_workbaskets")
def test_workbasket_transition(upload, workbasket, transition, valid_user):
    """Tests all combinations of initial workbasket status and transition,
    testing that valid transitions do not error, and invalid transitions raise
    TransitionNotAllowed."""

    transition_args = (
        [valid_user.pk, "SEED_FIRST"] if transition.name == "queue" else []
    )

    try:
        getattr(workbasket, transition.name)(*transition_args)
        assert workbasket.status == transition.target.value
    except TransitionNotAllowed:
        assert transition.name not in {
            t.name for t in workbasket.get_available_status_transitions()
        }


@patch("exporter.tasks.upload_workbaskets")
def test_workbasket_transition_task(upload, workbasket, transition, valid_user):
    """Tests all combinations of initial workbasket status and transition,
    testing that valid transitions do not error, and invalid transitions raise
    TransitionNotAllowed."""

    transition_args = (
        [valid_user.pk, "SEED_FIRST"] if transition.name == "queue" else []
    )

    try:
        tasks.transition(workbasket.pk, transition.name, *transition_args)
        workbasket.refresh_from_db()
        assert workbasket.status == transition.target.value
    except TransitionNotAllowed:
        assert transition.name not in {
            t.name for t in workbasket.get_available_status_transitions()
        }


def test_get_tracked_models(new_workbasket):
    for _ in range(2):
        factories.FootnoteFactory.create()

    assert TrackedModel.objects.count() > 2
    assert new_workbasket.tracked_models.count() == 2


@patch("exporter.tasks.upload_workbaskets")
def test_workbasket_accepted_updates_current_tracked_models(
    upload,
    assigned_workbasket,
    valid_user,
):
    original_footnote = factories.FootnoteFactory.create()
    new_footnote = original_footnote.new_version(
        workbasket=assigned_workbasket,
        update_type=UpdateType.UPDATE,
    )

    assert new_footnote.version_group.current_version.pk == original_footnote.pk

    assert_workbasket_valid(assigned_workbasket)

    assigned_workbasket.queue(valid_user.pk, settings.TRANSACTION_SCHEMA)
    new_footnote.refresh_from_db()

    assert new_footnote.version_group.current_version.pk == new_footnote.pk


@patch("exporter.tasks.upload_workbaskets")
def test_workbasket_errored_updates_tracked_models(
    upload,
    assigned_workbasket,
    valid_user,
    settings,
):
    settings.TRANSACTION_SCHEMA = "workbaskets.models.SEED_FIRST"
    original_footnote = factories.FootnoteFactory.create()
    new_footnote = original_footnote.new_version(
        workbasket=assigned_workbasket,
        update_type=UpdateType.UPDATE,
    )
    assert_workbasket_valid(assigned_workbasket)

    assigned_workbasket.queue(valid_user.pk, settings.TRANSACTION_SCHEMA)
    new_footnote.refresh_from_db()
    assert new_footnote.version_group.current_version.pk == new_footnote.pk
    assigned_workbasket.cds_error()
    new_footnote.refresh_from_db()
    assert new_footnote.version_group.current_version.pk == original_footnote.pk


@pytest.mark.parametrize("status", [WorkflowStatus.EDITING, WorkflowStatus.ERRORED])
def test_draft_status_as_transaction_partition_draft_no_first_seed(
    status,
):
    """When first_partition_is_seed is False, draft workbaskets should generate
    a DRAFT transaction partition value."""
    partition_scheme = SEED_FIRST
    assert isinstance(partition_scheme, TransactionPartitionScheme)

    partition = partition_scheme.get_partition(status)

    assert partition == TransactionPartition.DRAFT


@pytest.mark.parametrize("status", WorkflowStatus.approved_statuses())
@pytest.mark.parametrize(
    "partition_scheme,expected_partition",
    [
        (
            UserTransactionPartitionScheme(TransactionPartition.SEED_FILE, "test text"),
            TransactionPartition.SEED_FILE,
        ),
        (
            UserTransactionPartitionScheme(TransactionPartition.REVISION, "test text"),
            TransactionPartition.REVISION,
        ),
    ],
)
def test_user_partition_scheme_passes_queued_workbaskets(
    status,
    partition_scheme,
    expected_partition,
):
    """UserTransactionPartitionScheme get_partition should return its
    approved_partition on being passed an approved workbasket."""
    partition_result = partition_scheme.get_partition(status)
    assert partition_result == partition_scheme.get_approved_partition()
    assert partition_result == expected_partition


@pytest.mark.parametrize(
    "partition_scheme,expected_partition,command_line_name",
    [
        (SEED_ONLY, TransactionPartition.SEED_FILE, "SEED_ONLY"),
        (REVISION_ONLY, TransactionPartition.REVISION, "REVISION_ONLY"),
    ],
)
def test_user_partitions_have_expected_values(
    partition_scheme,
    expected_partition,
    command_line_name,
):
    """Verify UserTransactionPartitionScheme constants and fields contain
    expected values."""
    assert isinstance(partition_scheme, UserTransactionPartitionScheme)
    assert partition_scheme.approved_partition == expected_partition
    assert (
        partition_scheme.approved_partition == partition_scheme.get_approved_partition()
    )
    assert (
        command_line_name in TRANSACTION_PARTITION_SCHEMES
    ), f"Could not find {command_line_name} in {TRANSACTION_PARTITION_SCHEMES}"
    assert TRANSACTION_PARTITION_SCHEMES[command_line_name] is partition_scheme


def test_user_partition_scheme_does_not_accept_draft_as_approved_partition():
    """Verify that UserTransactionPartitionScheme get_partition return its
    approved_partition on being passed an approved workbasket."""
    with pytest.raises(ValueError):
        UserTransactionPartitionScheme(TransactionPartition.DRAFT, "test text")


@pytest.mark.parametrize(
    "transaction_factories",
    [
        (ApprovedTransactionFactory,),
        (SeedFileTransactionFactory, ApprovedTransactionFactory),
    ],
)
def test_user_partition_scheme_get_approved_partition_does_not_allow_seed_after_revision(
    transaction_factories: Iterable[TransactionFactory],
):
    """Verify that UserPartitionScheme won't allow a SEED transaction if there a
    REVISION transaction already exists (as this may effect global ordering)"""
    for factory in transaction_factories:
        factory.create()

    with pytest.raises(ValueError):
        SEED_ONLY.get_approved_partition()


@pytest.mark.parametrize(
    "transaction_factories",
    [
        (ApprovedTransactionFactory,),
        (SeedFileTransactionFactory, ApprovedTransactionFactory),
    ],
)
@pytest.mark.parametrize("status", WorkflowStatus.approved_statuses())
def test_user_partition_scheme_get_partition_does_not_allow_seed_after_revision(
    transaction_factories: Iterable[TransactionFactory],
    status: WorkflowStatus,
):
    """Verify that UserPartitionScheme won't allow a SEED transaction if there a
    REVISION transaction already exists (as this may effect global ordering)"""
    for factory in transaction_factories:
        factory.create()

    with pytest.raises(ValueError):
        SEED_ONLY.get_partition(status)


@pytest.mark.parametrize(
    "partition_setting,expected_partition",
    [
        ("workbaskets.models.REVISION_ONLY", TransactionPartition.REVISION),
        ("workbaskets.models.SEED_ONLY", TransactionPartition.SEED_FILE),
        ("workbaskets.models.SEED_FIRST", TransactionPartition.SEED_FILE),
    ],
)
def test_workbasket_approval_updates_transactions(
    settings,
    valid_user,
    partition_setting,
    expected_partition,
):
    """Verify that queuing an EDITING workbasket moves its DRAFT transactions to
    SEED_FILE or REVISION as specified by the partition scheme, and that the
    transaction order is updated to start at the end of the specified
    partition."""
    # This test is good at finding issues with factories that implicitly create transactions
    # in the wrong order.
    settings.TRANSACTION_SCHEMA = partition_setting
    partition_scheme = get_partition_scheme()

    # Sanity check result of get_partition_scheme before continuing
    assert isinstance(partition_scheme, TransactionPartitionScheme)
    if isinstance(partition_scheme, UserTransactionPartitionScheme):
        assert partition_scheme.approved_partition == expected_partition

    new_workbasket = WorkBasketFactory.create(status=WorkflowStatus.EDITING)
    assert type(new_workbasket).objects.count() == 1

    model = factories.FootnoteFactory.create(
        transaction=new_workbasket.new_transaction(),
    )
    assert model.transaction.partition == TransactionPartition.DRAFT

    # Before approving the workbasket check the ground truth that it contains some draft transactions.
    assert [TransactionPartition.DRAFT] == list(
        new_workbasket.transactions.distinct("partition").values_list(
            "partition",
            flat=True,
        ),
    )
    new_workbasket.approve(valid_user.pk, partition_setting)

    assert [expected_partition] == list(
        new_workbasket.transactions.distinct("partition").values_list(
            "partition",
            flat=True,
        ),
    )

    assert_transaction_order(Transaction.objects.all())


def test_current_transaction_returns_last_approved_transaction(
    session_request,
    approved_transaction,
):
    """Check that when no workbasket is saved on the request session
    get_current_transaction returns the latest approved transaction instead."""
    current = WorkBasket.get_current_transaction(session_request)

    assert current == approved_transaction


@pytest.mark.parametrize(
    "method, source, target",
    [
        ("archive", "EDITING", "ARCHIVED"),
        ("unarchive", "ARCHIVED", "EDITING"),
        ("dequeue", "QUEUED", "EDITING"),
        ("cds_confirmed", "QUEUED", "PUBLISHED"),
        ("cds_error", "QUEUED", "ERRORED"),
        ("restore", "ERRORED", "EDITING"),
    ],
)
def test_workbasket_transition_methods(method, source, target):
    """Test that workbasket transition methods move workbasket status from
    source to target."""

    wb = factories.WorkBasketFactory.create(status=getattr(WorkflowStatus, source))
    getattr(wb, method)()

    assert wb.status == getattr(WorkflowStatus, target)


def test_workbasket_transition_archive_not_empty():
    """Tests that a non-empty workbasket cannot be transitioned to ARCHIVED
    status."""
    workbasket = factories.WorkBasketFactory.create(status=WorkflowStatus.EDITING)
    footnote = factories.FootnoteFactory.create(
        transaction=workbasket.new_transaction(),
    )
    with pytest.raises(TransitionNotAllowed):
        workbasket.archive()
        assert workbasket.status == WorkflowStatus.EDITING


def test_queue(valid_user, unapproved_checked_transaction):
    """Test that approve transitions workbasket from EDITING to QUEUED, setting
    approver and shifting transaction from DRAFT to REVISION partition."""
    wb = unapproved_checked_transaction.workbasket
    task = factories.TaskFactory.create(workbasket=wb)
    factories.TaskAssigneeFactory.create(
        assignment_type=TaskAssignee.AssignmentType.WORKBASKET_WORKER,
        task=task,
    )
    factories.TaskAssigneeFactory.create(
        assignment_type=TaskAssignee.AssignmentType.WORKBASKET_REVIEWER,
        task=task,
    )
    wb.queue(valid_user.pk, settings.TRANSACTION_SCHEMA)

    assert wb.status == WorkflowStatus.QUEUED
    assert wb.approver == valid_user

    for transaction in wb.transactions.all():
        assert transaction.partition == TransactionPartition.REVISION


def test_workbasket_rule_check_progress():
    """Tests that `rule_check_progress()` returns the number of completed
    transaction checks and total number of transactions to be checked for the
    workbasket."""
    workbasket = factories.WorkBasketFactory.create()
    transactions = TransactionFactory.create_batch(3, workbasket=workbasket)
    check = TransactionCheckFactory.create(transaction=transactions[0], completed=True)
    num_completed, total = workbasket.rule_check_progress()
    assert num_completed == 1
    assert total == len(transactions)


def test_workbasket_purge_transactions():
    """Test that attempts to purge empty transactions from a workbasket only
    removes those that are empty, leaving non-empty ones intact."""

    workbasket = factories.WorkBasketFactory.create(status=WorkflowStatus.EDITING)
    transactions = TransactionFactory.create_batch(2, workbasket=workbasket)
    model = factories.TestModel1Factory.create(transaction=transactions[0])

    assert workbasket.transactions.count() == 2

    delete_count = workbasket.purge_empty_transactions()

    assert delete_count == 1
    assert workbasket.transactions.count() == 1
    assert model.transaction.pk == workbasket.transactions.get().pk


@pytest.mark.parametrize(
    "workbasket_status,",
    (*WorkflowStatus.non_editing_statuses(),),
)
def test_invalid_workbasket_purge_transactions(workbasket_status):
    """Test that efforts to purge empty transactions from non-EDITING
    workbaskets fails."""

    workbasket = factories.WorkBasketFactory.create(status=workbasket_status)
    transactions = TransactionFactory.create_batch(2, workbasket=workbasket)
    factories.TestModel1Factory.create(transaction=transactions[0])

    assert workbasket.transactions.count() == 2

    with pytest.raises(TransactionPurgeException):
        workbasket.purge_empty_transactions()

    assert workbasket.transactions.count() == 2


def test_workbasket_set_as_current(valid_user, workbasket):
    """Test that set_as_current() sets the workbasket instance as the user's
    current workbasket."""
    assert not valid_user.current_workbasket
    workbasket.set_as_current(valid_user)
    assert valid_user.current_workbasket == workbasket


def test_unassigned_workbasket_cannot_be_queued():
    """Tests that an unassigned workbasket is marked as not fully assigned and
    cannot be queued."""
    workbasket = factories.WorkBasketFactory.create()
    assert not workbasket.is_fully_assigned()

    worker = factories.UserFactory.create()
    task = factories.TaskFactory.create(workbasket=workbasket)

    with pytest.raises(TransitionNotAllowed):
        workbasket.queue(user=worker.id, scheme_name=settings.TRANSACTION_SCHEMA)

    factories.TaskAssigneeFactory.create(
        user=worker,
        assignment_type=TaskAssignee.AssignmentType.WORKBASKET_WORKER,
        task=task,
    )
    factories.TaskAssigneeFactory.create(
        assignment_type=TaskAssignee.AssignmentType.WORKBASKET_REVIEWER,
        task=task,
    )
    assert workbasket.is_fully_assigned()

    TaskAssignee.unassign_user(user=worker, task=task)
    assert not workbasket.is_fully_assigned()


def test_workbasket_user_assignments_queryset():
    workbasket = factories.WorkBasketFactory.create()
    worker_assignment = factories.TaskAssigneeFactory.create(
        assignment_type=TaskAssignee.AssignmentType.WORKBASKET_WORKER,
        task__workbasket=workbasket,
    )
    reviewer_assignment = factories.TaskAssigneeFactory.create(
        assignment_type=TaskAssignee.AssignmentType.WORKBASKET_REVIEWER,
        task__workbasket=workbasket,
    )
    # Inactive assignment
    factories.TaskAssigneeFactory.create(
        unassigned_at=datetime.now(),
        task__workbasket=workbasket,
    )
    # Unrelated assignment
    factories.TaskAssigneeFactory.create()

    workbasket.refresh_from_db()
    queryset = workbasket.user_assignments

    assert worker_assignment in queryset
    assert reviewer_assignment in queryset
    assert len(queryset) == 2
