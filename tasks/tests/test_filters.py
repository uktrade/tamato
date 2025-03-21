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
        (f"{settings.TICKET_PREFIX}-1234", True),
        ("1234", True),
        ("4321", False),
    ],
)
def test_ticket_id_filter(search_term, expected_result):
    """Test that a user searching by a prefixed ticket ID correctly returns
    results regardless of case or if the dash is included."""

    ticket_filter = TaskWorkflowFilter()
    summary_task = TaskFactory.create()
    TaskWorkflowFactory.create(summary_task=summary_task, id=1234)
    queryset = Task.objects.all()

    filtered_steps = ticket_filter.filter_search(queryset, "search", search_term)
    assert (summary_task in filtered_steps) == expected_result


@pytest.mark.parametrize("ticket_prefix", [("TC2025"), ("TC2025-"), ("")])
def test_alternative_ticket_prefixes(ticket_prefix):
    """Test that filtering still works with a prefix including numbers or no
    prefix at all."""
    settings.TICKET_PREFIX = ticket_prefix

    ticket_filter = TaskWorkflowFilter()
    summary_task = TaskFactory.create()
    TaskWorkflowFactory.create(summary_task=summary_task, id=1234)
    queryset = Task.objects.all()

    search_term = f"{ticket_prefix}1234"
    filtered_steps = ticket_filter.filter_search(queryset, "search", search_term)
    assert (summary_task in filtered_steps) == True
