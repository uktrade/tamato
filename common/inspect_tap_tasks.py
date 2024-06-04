from datetime import datetime
from typing import Dict
from typing import List

from django.utils.timezone import make_aware

from common.celery import app
from workbaskets.models import WorkBasket


class TAPTasks:
    """Get and filter Celery tasks on TAP's Celery queues."""

    @staticmethod
    def timestamp_to_datetime_string(timestamp) -> datetime:
        """Utility function used to convert a timestamp to a string formatted
        representation."""
        return make_aware(
            datetime.fromtimestamp(timestamp),
        ).strftime("%d %b %Y, %H:%M")

    def active_tasks(self, task_name=None):
        """Returns a dictionary of the application's currently active Celery
        tasks."""
        inspect = app.control.inspect()
        if not inspect:
            return {}

        active_tasks = inspect.active()
        if not active_tasks:
            return {}

        tasks = active_tasks.values()
        # Cleaning out celery workers? with no current tasks
        tasks_cleaned = [item for item in tasks if len(item) != 0][0]

        if task_name:
            filtered_active_tasks = [
                task for task in tasks_cleaned if task["name"] == task_name
            ]
            return filtered_active_tasks

        return [task for task in tasks_cleaned]

    def queued_tasks(self, task_name=None):
        """Returns a dictionary of the application's currently queued Celery
        tasks."""
        inspect = app.control.inspect()
        if not inspect:
            return {}

        queued_tasks = inspect.reserved()
        if not queued_tasks:
            return {}

        tasks = queued_tasks.values()
        # Cleaning out celery workers? with no current tasks
        tasks_cleaned = [item for item in tasks if len(item) != 0][0]

        if task_name:
            filtered_active_tasks = [
                task for task in tasks_cleaned if task["name"] == task_name
            ]
            return filtered_active_tasks

        return [task for task in tasks_cleaned]

    def current_rule_checks(self, task_name=None) -> List[Dict]:
        """Return a list of dictionaries, each describing currently active or
        queued business rule checking tasks."""
        results = []

        due_tasks = self.active_tasks(task_name=task_name) + self.queued_tasks(
            task_name=task_name,
        )

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
            status = "Active" if time_start else "Queued"

            results.append(
                {
                    "task_id": task_info["id"],
                    "workbasket_id": workbasket_id,
                    "date_time_start": date_time_start,
                    "checks_completed": f"{num_completed} out of {total}",
                    "status": status,
                },
            )

        return results
