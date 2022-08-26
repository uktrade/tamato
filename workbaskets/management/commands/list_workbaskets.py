import ast
import logging
from typing import Any
from typing import Optional

from django.core.management import BaseCommand
from django.core.management.base import CommandParser

from workbaskets.management.util import WorkBasketCommandMixin
from workbaskets.management.util import WorkBasketOutputFormat
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus

logger = logging.getLogger(__name__)


class Command(WorkBasketCommandMixin, BaseCommand):
    help = "List WorkBasket details."

    def add_arguments(self, parser: CommandParser) -> None:
        statuses = [str(w) for w in WorkflowStatus]
        parser.add_argument(
            "--status",
            nargs="+",
            help=(
                "Only list WorkBaskets with the given STATUS. The default, "
                "without use of this flag, is to list all WorkBaskets."
                f"STATUS can be any of {', '.join(statuses)}"
            ),
        )

        approved_statuses = [
            status.name for status in WorkflowStatus.approved_statuses()
        ]
        parser.add_argument(
            "-a",
            "--approved-statuses",
            dest="approved",
            action="store_true",
            help=f"List workbaskets with ANY of the approved statuses, equivalent to: [{', '.join(approved_statuses)}]",
        )

        parser.add_argument(
            "-c",
            "--compact",
            action="store_true",
            help="Output one workbasket per line.",
        )

        parser.add_argument(
            "-t",
            "--transactions",
            action="store_true",
            help="Output first / last transactions.",
        )

        parser.add_argument(
            "workbasket_ids",
            help=("Comma-separated list of workbasket ids to filter to"),
            type=ast.literal_eval,
        )

    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        workbaskets = WorkBasket.objects.order_by("updated_at").all()

        workbasket_statuses = set()
        if options["status"]:
            workbasket_statuses.update(options["status"])

        if options.get("approved_statuses"):
            workbasket_statuses.update(WorkflowStatus.approved_statuses())

        if workbasket_statuses:
            workbaskets = workbaskets.filter(status__in=options["status"])

        if options.get("workbasket_ids"):
            workbaskets = workbaskets.filter(id__in=options["workbasket_ids"])

        output_format = (
            WorkBasketOutputFormat.COMPACT
            if options["compact"]
            else WorkBasketOutputFormat.READABLE
        )

        show_transaction_info = options["transactions"]

        self.output_workbaskets(
            workbaskets,
            show_transaction_info,
            output_format=output_format,
        )
