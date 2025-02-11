import itertools
from dataclasses import dataclass
from datetime import datetime
from typing import Dict
from typing import List

from django.conf import settings
from django.utils.timezone import make_aware

from common.celery import app
from common.tasks_constants import *
from workbaskets.models import WorkBasket

TASK_NAME_MAPPING = {
    RULE_CHECK_NAME: "Rule check",
    MISSING_MEASURES_CHECK_NAME: "Missing measures check",
}


@dataclass
class CeleryTask:
    """Data class for active and queued celery tasks."""

    task_id: str
    verbose_name: str
    workbasket_id: int
    date_time_start: str
    progress: str
    status: str


class TAPTasks:
    """Get and filter Celery tasks on TAP's Celery queues."""

    @staticmethod
    def timestamp_to_datetime_string(timestamp) -> datetime:
        """Utility function used to convert a timestamp to a string formatted
        representation."""
        return make_aware(
            datetime.fromtimestamp(timestamp),
        ).strftime(settings.DATETIME_FORMAT)

    def clean_tasks(self, tasks, task_status="", routing_key="") -> List[Dict]:
        """Return a list of dictionaries, each describing Celery task, adding
        the given status."""
        if not tasks:
            return []

        # tasks should be a dictionary of {celery worker : [related tasks]}
        # tasks.values() therefore is a list of lists of celery tasks grouped by worker
        tasks_cleaned = []
        for task in tasks.values():
            for item in task:
                if item:
                    item["status"] = task_status
                    tasks_cleaned.append(item)

        # see settings.common.CELERY_ROUTES
        if routing_key:
            filtered_active_tasks = [
                task
                for task in tasks_cleaned
                if task["delivery_info"]["routing_key"] == routing_key
            ]
            return filtered_active_tasks

        return tasks_cleaned

    def current_tasks(self, routing_key="") -> List[CeleryTask]:
        """Return the list of tasks queued or started, ready to display in the
        view."""

        due_tasks = self.get_due_tasks(routing_key)

        results = []

        for task_info in due_tasks:
            time_start = task_info["time_start"]
            date_time_start = (
                self.timestamp_to_datetime_string(time_start)
                if time_start is not None
                else None
            )

            workbasket_id = task_info["args"][0]
            progress = self.get_task_progress(workbasket_id, task_info["name"])
            results.append(
                CeleryTask(
                    task_info["id"],
                    TASK_NAME_MAPPING[task_info["name"]],
                    workbasket_id,
                    date_time_start,
                    progress,
                    task_info["status"],
                ),
            )

        return results

    def get_due_tasks(self, routing_key="") -> List[Dict]:
        inspect = app.control.inspect()
        if not inspect:
            return []

        due_tasks = []

        due_tasks += self.clean_tasks(
            inspect.active(),
            task_status="Active",
            routing_key=routing_key,
        ) + self.clean_tasks(
            inspect.reserved(),
            task_status="Queued",
            routing_key=routing_key,
        )

        # Remove any lingering tasks that have actually been revoked
        if inspect.revoked():
            revoked_tasks = list(itertools.chain(*inspect.revoked().values()))
            due_tasks = [task for task in due_tasks if task["id"] not in revoked_tasks]

        return due_tasks

    def get_task_progress(self, workbasket_id, name):
        workbasket = WorkBasket.objects.get(id=workbasket_id)

        if name == RULE_CHECK_NAME:
            num_completed, total = workbasket.rule_check_progress()
            return f"{num_completed} out of {total}"

        if name == MISSING_MEASURES_CHECK_NAME:
            num_completed, total = workbasket.missing_measure_check_progress()
            return f"{num_completed} out of {total}"

        return ""
