import logging
import re
import signal
import sys
from typing import Any
from typing import Dict
from typing import Optional

from celery.result import AsyncResult
from celery.result import EagerResult
from celery.result import GroupResult
from django.core.management import BaseCommand
from django.core.management.base import CommandParser

from checks.models import BusinessRuleModel
from checks.models import TrackedModelCheck
from common.models import TrackedModel
from workbaskets.models import WorkBasket

logger = logging.getLogger(__name__)

CLEAR_TO_END_OF_LINE = "\x1b[K"


def revoke_task_and_children(task, depth=0):
    """
    Revoke a task by task_id.

    Uses SIGUSR1, which invokes the SoftTimeLimitExceeded exception, this is
    more friendly than plain terminate, which may kill other tasks in the
    worker.
    """
    if task.children:
        for subtask in task.children:
            yield from revoke_task_and_children(subtask, depth + 1)

    task.revoke(terminate=True, signal="SIGUSR1")
    yield task, depth


class TaskControlMixin:
    # Implementing classes can remove the module names of tasks to make the display less verbose.
    IGNORE_TASK_PREFIXES = []

    def get_readable_task_name(self, node):
        """Optionally remove a prefix from the task name (used to remove the
        module which is often repeated)"""
        if isinstance(node, EagerResult) and not node.name:
            # Name isn't available for when CELERY_TASK_ALWAYS_EAGER is set :(
            return f"Eager Task: {node.id}"

        task_name = getattr(node, "name") or ""
        for prefix in self.IGNORE_TASK_PREFIXES:
            unprefixed = task_name.replace(prefix, "")
            if unprefixed != task_name:
                return unprefixed

        return task_name

    def revoke_task_and_children_and_display_result(self, task):
        """Call revoke_task_and_children and display information on each revoked
        task."""
        for revoked_task, depth in revoke_task_and_children(task):
            if isinstance(task, AsyncResult):
                self.stdout.write(
                    " " * depth
                    + f"{getattr(revoked_task, 'name', None) or '-'}  [{revoked_task.id}] {revoked_task.status}",
                )

    def revoke_task_on_sigint(self, task):
        """
        Connect a signal handler to attempt to revoke a task if the user presses
        Ctrl+C.

        Due to the way tasks travel through Celery, not all tasks can be
        revoked.
        """

        def sigint_handler(sig, frame):
            """Revoke celery task with task_id."""
            self.stdout.write(f"Received SIGINT, revoking task {task.id} and children.")
            self.revoke_task_and_children_and_display_result(task)

            raise SystemExit(1)

        signal.signal(signal.SIGINT, sigint_handler)

    def display_task(self, node, value, depth):
        """Default task display."""
        # Only shows task.args, to avoid some noise.
        readable_task_name = self.get_readable_task_name(
            node,
        )

        # node.args can be None when CELERY_TASK_ALWAYS_EAGER is set,
        # - when running eagerly the full API isn't available.
        self.stdout.write(
            " " * depth * 2 + f"{readable_task_name}  " + f"{tuple(node.args or ())}",
        )

    def iterate_ongoing_tasks(self, result, ignore_groupresult=True):
        """
        Iterate over the ongoing tasks as they are received, "depth" is tracked
        to enabled visual formatting.

        Yields: (node, value, depth)
        """
        task_depths: Dict[str, int] = {result.id: 0}

        for parent_id, node in result.iterdeps(intermediate=True):
            value = node.get()

            depth = task_depths.get(parent_id, -1)
            if isinstance(node, GroupResult) and ignore_groupresult:
                # GroupResult is ignored:  store it so looking up depth works
                # but do not increase the indent..
                task_depths[node.id] = depth
                continue
            else:
                task_depths[node.id] = depth + 1

            yield node, value, depth

    def display_ongoing_tasks(self, result):
        """Iterate the task tree and display info as the received."""
        for node, value, depth in self.iterate_ongoing_tasks(result):
            self.display_task(node, value, depth)


def is_check_model_task(node):
    return getattr(node, "name", None) == "checks.tasks.check_model"


class Command(TaskControlMixin, BaseCommand):
    IGNORE_TASK_PREFIXES = [
        "checks.tasks.",
    ]

    rule_names = []
    rule_models = None
    passed = 0
    failed = 0

    help = (
        "Run all business rule checks against a WorkBasket's TrackedModels in Celery."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("WORKBASKET_PK", type=int)
        parser.add_argument("--clear-cache", action="store_true", default=False)
        parser.add_argument(
            "--throw",
            help="Allow failing celery tasks to throw exceptions [dev setting]",
            action="store_true",
            default=False,
        )

        parser.add_argument(
            "rules",
            type=str,
            nargs="*",
            help="Check only these rules (comma seperated list):  'rule_name1,rule_name2'",
        )

    def display_check_model_task(self, node, value, depth):
        model_pk = node.args[1]
        check_passed = value
        readable_task_name = self.get_readable_task_name(node)
        style = self.style.SUCCESS if check_passed else self.style.ERROR

        model = TrackedModel.objects.get(pk=model_pk)
        check = TrackedModelCheck.objects.filter(model=model_pk).last()

        if check is None:
            check_msg = f"[{model}]  [All checks pending]"
        else:
            check_msg = check.report(self.rule_models)

        self.stdout.write(
            " " * depth * 2
            + f"{readable_task_name}  "
            + style(
                f"[{model_pk}] {check_msg}",
            ),
        )

    def display_task(self, node, value, depth):
        """Custom display for check_model tasks, acculate their passes /
        fails."""
        if is_check_model_task(node):
            self.display_check_model_task(node, value, depth)
        else:
            super().display_task(node, value, depth)

    def iterate_ongoing_tasks(self, result, ignore_groupresult=True):
        """Custom task iterator to accumulate passes and fails."""
        for node, value, depth in super().iterate_ongoing_tasks(result):
            if is_check_model_task(node):
                if value:
                    self.passed += 1
                else:
                    self.failed += 1
            yield node, value, depth

    def parse_rule_names_option(self, rule_names_option: Optional[str]):
        """
        Given a comma seperated list of rule names, return a list of rule names
        and a list of their corresponding models.

        Also handles the case where the user includes spaces.
        """

        if not rule_names_option:
            return [], None

        # Split by comma, but be kind and eat spaces too.
        rule_names = re.split(r"\s|,", rule_names_option)

        # The user may limit the check to particular rules.
        if rule_names:
            rule_names = rule_names
            rule_models = BusinessRuleModel.objects.current().filter(
                name__in=rule_names,
            )
            if rule_models.count() != len(rule_names):
                # TODO - be nice to the user and show which rules are missing.
                self.stderr.write(
                    "One or more rules not found:  " + ", ".join(rule_names),
                )
                sys.exit(2)
            return rule_names, rule_models
        else:
            # None, defaults to all rules being checks.
            return None, None

    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        from checks.tasks import check_workbasket

        # Get the workbasket first
        workbasket = WorkBasket.objects.get(
            pk=int(options["WORKBASKET_PK"]),
        )
        clear_cache = options["clear_cache"]
        throw = options["throw"]

        self.rule_names, self.rule_models = self.parse_rule_names_option(
            options["rules"],
        )

        # Temporarily display a message while waiting for celery to acknowledge the task,
        # if this stays on the screen it's a sign celery is either busy or not running.
        self.stdout.write("Connecting to celery...  ⌛", ending="")
        self.stdout._out.flush()  # self.stdout.flush() doesn't result in any output - TODO: report as a bug to django.
        result = check_workbasket.apply_async(
            args=(
                workbasket.pk,
                None,
            ),
            kwargs={
                "clear_cache": clear_cache,
                "rules": self.rule_names,
            },
            throw=throw,
        )
        result.wait()
        self.stdout.write(f"\r{CLEAR_TO_END_OF_LINE}")

        # Attach a handler to revoke the task and its subtasks if the user presses Ctrl+C
        self.revoke_task_on_sigint(result)

        # Display tasks as they complete
        self.display_ongoing_tasks(result)
        self.stdout.write()

        style = self.style.ERROR if self.failed else self.style.SUCCESS
        self.stdout.write(style(f"Failed: {self.failed}"))
        self.stdout.write(style(f"Passed: {self.passed}"))
        self.stdout.write()

        sys.exit(1 if self.failed else 0)
