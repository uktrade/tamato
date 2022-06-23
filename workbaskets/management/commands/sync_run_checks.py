import logging
from typing import Any
from typing import Optional

from django.core.management import BaseCommand
from django.core.management.base import CommandParser

from checks.tasks import check_workbasket_sync
from workbaskets.management.util import WorkBasketCommandMixin
from workbaskets.models import WorkBasket

logger = logging.getLogger(__name__)


class Command(WorkBasketCommandMixin, BaseCommand):
    help = (
        "Synchronously run all business rule checks against a WorkBasket's "
        "Transactions and associated TrackedModels."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("WORKBASKET_PK", type=int)

    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        workbasket = WorkBasket.objects.get(
            pk=int(options["WORKBASKET_PK"]),
        )
        self.stdout.write(
            f"Starting business rule checks against WorkBasket {workbasket}...",
        )
        workbasket.delete_checks()
        # Generate new TransactionCheck and TrackedModelCheck instances for
        # this WorkBasket.
        check_workbasket_sync(workbasket)
        check_errors = workbasket.tracked_model_check_errors
        if check_errors:
            self.stdout.write(
                self.style.ERROR(f"{check_errors.count()} error(s) found."),
            )
            for error in check_errors:
                message = (
                    error.message if error.message else "(Error message unavailable)"
                )
                self.stdout.write(
                    self.style.NOTICE(
                        f"{error.check_name} {error.model} {message}.",
                    ),
                )
        else:
            self.stdout.write(self.style.SUCCESS("No errors found."))
