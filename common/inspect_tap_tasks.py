import itertools
from dataclasses import dataclass
from datetime import datetime
from typing import Dict
from typing import List

from django.conf import settings
from django.utils.timezone import make_aware

from common.celery import app
from workbaskets.models import WorkBasket


@dataclass
class CeleryTask:
    """Data class for active and queued celery tasks."""

    task_id: str
    workbasket_id: int
    date_time_start: str
    checks_completed: str
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

    def clean_tasks(self, tasks, task_status="", task_name="") -> List[Dict]:
        """Return a list of dictionaries, each describing Celery task, adding
        the given status."""
        if not tasks:
            return []

        # tasks_info should be a dictionary of {celery worker : [related tasks]}
        # tasks_info.values() therefore is a list of lists of celery tasks grouped by worker
        tasks_cleaned = []
        for task in tasks.values():
            for item in task:
                if item:
                    item["status"] = task_status
                    tasks_cleaned.append(item)

        # As we cannot filter by worker name (in this case rule-check-worker), it filters by task name supplied when
        # initialising the class

        if task_name:
            filtered_active_tasks = [
                task for task in tasks_cleaned if task["name"] == task_name
            ]
            return filtered_active_tasks

        return tasks_cleaned

    def current_rule_checks(self, task_name="") -> List[CeleryTask]:
        """Return the list of tasks queued or started, ready to display in the
        view."""
        inspect = app.control.inspect()
        if not inspect:
            return []

        due_tasks = self.clean_tasks(
            inspect.active(),
            task_status="Active",
            task_name=task_name,
        ) + self.clean_tasks(
            inspect.reserved(),
            task_status="Queued",
            task_name=task_name,
        )

        # Remove any lingering tasks that have actually been revoked
        if inspect.revoked():
            revoked_tasks = list(itertools.chain(*inspect.revoked().values()))
            due_tasks = [task for task in due_tasks if task["id"] not in revoked_tasks]

        results = []

        for task_info in due_tasks:
            time_start = task_info["time_start"]
            date_time_start = (
                self.timestamp_to_datetime_string(time_start)
                if time_start is not None
                else None
            )

            workbasket_id = task_info["args"][0]
            workbasket = WorkBasket.objects.get(id=workbasket_id)
            num_completed, total = workbasket.rule_check_progress()

            # results.append(
            #     {
            #         "task_id": task_info["id"],
            #         "workbasket_id": workbasket_id,
            #         "date_time_start": date_time_start,
            #         "checks_completed": f"{num_completed} out of {total}",
            #         "status": task_info["status"],
            #     },
            # )
            results.append(
                CeleryTask(
                    task_info["id"],
                    workbasket_id,
                    date_time_start,
                    f"{num_completed} out of {total}",
                    task_info["status"],
                ),
            )

        return results
