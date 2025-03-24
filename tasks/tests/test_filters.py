import pytest
from django.conf import settings

from common.tests.factories import TaskFactory
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
