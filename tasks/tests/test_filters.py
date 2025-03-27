import pytest
from django.conf import settings

from common.tests.factories import TaskFactory
from common.tests.factories import UserFactory
from tasks.filters import TaskWorkflowFilter
from tasks.models import Task
from tasks.tests.factories import TaskWorkflowFactory

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "search_term, expected_result",
    [
        (f"{settings.TICKET_PREFIX}1234", True),
        (f"{settings.TICKET_PREFIX.lower()}1234", True),
        ("1234", True),
        ("4321", False),
    ],
)
def test_ticket_id_filter(search_term, expected_result):
    """Test that a user searching by a prefixed ticket ID correctly returns
    results regardless of case or prefix."""

    ticket_filter = TaskWorkflowFilter()
    summary_task = TaskFactory.create()
    TaskWorkflowFactory.create(summary_task=summary_task, id=1234)
    queryset = Task.objects.all()

    filtered_steps = ticket_filter.filter_search(queryset, "search", search_term)
    assert (summary_task in filtered_steps) == expected_result


@pytest.mark.parametrize(
    ("ticket_prefix", "search_sentence", "expected_result"),
    (
        ("", "", ""),
        ("", "123", "123"),
        ("", "ABC", "ABC"),
        ("", "123 456", "123 456"),
        ("TC-", "123", "123"),
        ("TC-", "TC-123", "123"),
        ("TC-", "TC-123 456", "123 456"),
        ("TC-", "TC-ABC", "TC-ABC"),
        ("TC-", "TC-ABC 123", "TC-ABC 123"),
        ("TC-", "TC-ABC TC-123", "TC-ABC 123"),
        ("2025", "2025123", "123"),
        ("2025", "2025ABC 123", "2025ABC 123"),
    ),
)
def test_normalise_prefixed_ticket_ids(
    ticket_prefix,
    search_sentence,
    expected_result,
):
    """Test that TaskWorkflowFilter.normalise_prefixed_ticket_ids() returns a
    normalised sentence with ticket ID prefixes removed correctly."""

    settings.TICKET_PREFIX = ticket_prefix

    ticket_filter = TaskWorkflowFilter()
    normalised_sentence = ticket_filter.normalise_prefixed_ticket_ids(
        search_sentence=search_sentence,
    )

    assert normalised_sentence == expected_result


@pytest.mark.parametrize(
    ("workflow_fixture", "assignment_status", "expected_filtered_count"),
    [
        (["assigned_task_workflow"], ["assigned"], 1),
        (["task_workflow"], ["not_assigned"], 1),
        (["assigned_task_workflow", "task_workflow"], ["assigned", "not_assigned"], 2),
        (["unassigned_task_workflow"], ["not_assigned"], 1),
        (["task_workflow", "unassigned_task_workflow"], ["not_assigned"], 2),
        (["unassigned_task_workflow", "assigned_task_workflow"], ["assigned"], 1),
        (
            ["unassigned_task_workflow", "assigned_task_workflow"],
            ["assigned", "not_assigned"],
            2,
        ),
        (
            ["unassigned_task_workflow", "assigned_task_workflow", "task_workflow"],
            ["assigned", "not_assigned"],
            3,
        ),
        (["task_workflow", "unassigned_task_workflow"], ["assigned"], 0),
    ],
)
def test_filter_by_assignment_status_workflow_list_view(
    workflow_fixture,
    assignment_status,
    expected_filtered_count,
    request,
):
    """Tests if tickets with differing assignment statuses (assigned) or
    (unassiged & never assigned) can be returned correctly when using the
    assignment status filter."""
    [request.getfixturevalue(fixture) for fixture in workflow_fixture]
    queryset = Task.objects.all()

    filter = TaskWorkflowFilter(queryset=queryset)
    filtered = filter.filter_by_assignment_status(
        queryset,
        assignment_status,
        assignment_status,
    )

    assert filtered.count() == expected_filtered_count


@pytest.mark.parametrize(
    ("workflow_fixture", "expected_filtered_count"),
    [
        (["assigned_task_workflow"], 0),
        (["task_workflow"], 0),
        (["task_workflow", "assigned_task_workflow"], 0),
        (["unassigned_task_workflow"], 0),
    ],
)
def test_filter_by_workflow_assignee(
    workflow_fixture,
    expected_filtered_count,
    request,
):
    """Tests if tickets that have been assigned to a user are returned correctly
    when filtering by assignee."""

    test_user = UserFactory.create()
    queryset = Task.objects.all()
    [request.getfixturevalue(fixture) for fixture in workflow_fixture]

    filter = TaskWorkflowFilter(queryset=queryset)
    filtered = filter.filter_by_current_assignee(queryset, "assignee", test_user)

    assert filtered.count() == expected_filtered_count
