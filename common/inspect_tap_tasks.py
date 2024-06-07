from datetime import datetime
from typing import Dict
from typing import List

from django.conf import settings
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
        ).strftime(settings.DATETIME_FORMAT)

    def clean_tasks(self, tasks_info, task_name=None, task_status="") -> List[Dict]:
        """Return a list of dictionaries, each describing Celery task,
        adding the given status """
        if not tasks_info:
            return []

        tasks = tasks_info.values()

        # Cleaning out celery workers? with no current tasks
        tasks_cleaned = [item for item in tasks if len(item) != 0]
        # The task_info.values() has a strange structure:
        # it is a list of list of dictionaries, with several empty entries
        #  if the entry is not empty,  only the first element contains the required
        tasks_cleaned = []
        for item in tasks:
            if len(item)  and len(item[0]):
                item[0]["status"]=task_status
                tasks_cleaned.append(item[0])

        if task_name:
            filtered_active_tasks = [
                task for task in tasks_cleaned if task["name"] == task_name
            ]
            return filtered_active_tasks

        return tasks_cleaned

    def current_rule_checks(self, task_name=None) -> List[Dict]:
        """ Return the list of tasks queued or started, ready to display in the view
        """
        inspect = app.control.inspect()
        if not inspect:
            return {}

        due_tasks = \
            self.clean_tasks(inspect.active(), task_name=task_name, task_status = "Active") + \
            self.clean_tasks(inspect.reserved(), task_name=task_name, task_status = "Queued")

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

            results.append(
                {
                    "task_id": task_info["id"],
                    "workbasket_id": workbasket_id,
                    "date_time_start": date_time_start,
                    "checks_completed": f"{num_completed} out of {total}",
                    "status": task_info["status"],
                },
            )

        return results
