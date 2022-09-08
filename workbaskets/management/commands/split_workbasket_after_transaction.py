import logging
from typing import Any
from typing import Optional

from django.core.management import BaseCommand
from django.core.management.base import CommandParser

from workbaskets.management.util import WorkBasketCommandMixin

logger = logging.getLogger(__name__)


class Command(WorkBasketCommandMixin, BaseCommand):
    help = (
        "Non-destructively split a workbasket into two other workbaskets, "
        "keeping the original source workbasket unchanged. The workbasket's "
        "transactions are split after the transaction given by TRANSASCTION_ID."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("WORKBASKET_PK", type=int)
        parser.add_argument(
            "TRANSACTION_ID",
            type=int,
            help=("A valid transaction ID in workbasket's associated " "transactions."),
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
        transaction_id = int(options["TRANSACTION_ID"])
        base_title = options["title"] or workbasket.title

        new_workbaskets = workbasket.split_after_transaction(
            transaction_id,
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
