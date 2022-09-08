import logging
from typing import Any
from typing import Optional

from django.core.management import BaseCommand
from django.core.management.base import CommandParser

from workbaskets.management.util import WorkBasketCommandMixin

logger = logging.getLogger(__name__)


class Command(WorkBasketCommandMixin, BaseCommand):
    help = (
        "Non-destructively split a workbasket into multiple other workbaskets, "
        "keeping the original source workbasket unchanged. Each newly created "
        "workbasket will contain a maximum count, MAX_TRANSACTIONS, of "
        "transactions."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("WORKBASKET_PK", type=int)
        parser.add_argument(
            "MAX_TRANSACTIONS",
            type=int,
            help=(
                "Maximum transactions per workbasket. A value of 0 (zero) will "
                "simply create a single copy of the source WorkBasket."
            ),
        )
        parser.add_argument(
            "--title",
            help=(
                "Base title used for newly created workbaskets. Default "
                "behaviour, without this optional parameter, is to use the "
                "title of the source workbasket."
            ),
        )

    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        workbasket = self.get_workbasket_or_exit(int(options["WORKBASKET_PK"]))
        max_transactions = int(options["MAX_TRANSACTIONS"])
        base_title = options["title"] or workbasket.title

        new_workbaskets = workbasket.split_by_transaction_count(
            max_transactions,
            base_title,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"WorkBasket {workbasket.pk} transactions split and copied to "
                f"{len(new_workbaskets)} new workbasket(s):",
            ),
        )
        for workbasket in new_workbaskets:
            self.output_workbasket(workbasket)
