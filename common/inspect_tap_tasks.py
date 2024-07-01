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

    def current_tasks(self, task_name="") -> List[CeleryTask]:
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


class TAPTasks2:
    """Get and filter Celery tasks on TAP's Celery queues."""

    @staticmethod
    def timestamp_to_datetime_string(timestamp) -> datetime:
        """Utility function used to convert a timestamp to a string formatted
        representation."""
        return make_aware(
            datetime.fromtimestamp(timestamp),
        ).strftime(settings.DATETIME_FORMAT)

    # @cached_property
    def _active_tasks(self) -> Dict:
        """Returns a dictionary of the application's currently active Celery
        tasks."""
        inspect = app.control.inspect()
        if not inspect:
            return {}

        active_tasks = inspect.active()
        if not active_tasks:
            return {}

        return active_tasks

    def active_envelope_creators(self) -> List[Dict]:
        """Return a list of dictionaries, each describing currently active
        envelope generation tasks."""

        results = []

        for _, task_info_list in self._active_tasks.items():
            # for task_info_list in self._active_tasks.values():
            for task_info in task_info_list:
                if task_info.get("name") == "publishing.tasks.create_xml_envelope_file":
                    date_time_start = TAPTasks2.timestamp_to_datetime_string(
                        task_info.get("time_start"),
                    )

                    packaged_workbasket_id = task_info.get("args", [""])[0]
                    packaged_workbasket = PackagedWorkBasket.objects.get(
                        id=packaged_workbasket_id,
                    )
                    workbasket_id = packaged_workbasket.workbasket.id

                    results.append(
                        {
                            "task_id": task_info.get("id"),
                            "workbasket_id": workbasket_id,
                            "date_time_start": date_time_start,
                            "packaged_workbasket_id": packaged_workbasket_id,
                        },
                    )

        return results

    def active_checks(self) -> List[Dict]:
        """Return a list of dictionaries, each describing currently active
        business rule checking tasks."""

        results = []

        for _, task_info_list in self._active_tasks.items():
            # for task_info_list in self._active_tasks.values():
            for task_info in task_info_list:
                if (
                    task_info.get("name")
                    == "workbaskets.tasks.call_check_workbasket_sync"
                ):
                    date_time_start = AppInfoView.timestamp_to_datetime_string(
                        task_info.get("time_start"),
                    )

                    workbasket_id = task_info.get("args", [""])[0]
                    workbasket = WorkBasket.objects.get(id=workbasket_id)
                    num_completed, total = workbasket.rule_check_progress()

                    results.append(
                        {
                            "task_id": task_info.get("id"),
                            "workbasket_id": workbasket_id,
                            "date_time_start": date_time_start,
                            "checks_completed": f"{num_completed} out of {total}",
                        },
                    )

        return results
