import logging
from typing import Any
from typing import Optional

from django.core.management import BaseCommand
from django.core.management.base import CommandParser

from workbaskets.management.util import WorkBasketCommandMixin
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus

logger = logging.getLogger(__name__)


class Command(WorkBasketCommandMixin, BaseCommand):
    help = "Transition a WorkBasket's status."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("WORKBASKET_PK", type=int)
        parser.add_argument("STATUS", choices=WorkflowStatus)

    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        workbasket = self.get_workbasket_or_exit(int(options["WORKBASKET_PK"]))
        if workbasket.status == options["STATUS"]:
            self.stdout.write(
                f"WorkBasket {workbasket.pk} is already in "
                f"{options['STATUS']} status.",
            )
            self.stdout.write("Exiting.")
            exit(0)

        other_editing_workbaskets = WorkBasket.objects.filter(
            status=WorkflowStatus.EDITING,
        ).exclude(pk=workbasket.pk)
        if (
            workbasket.status == WorkflowStatus.EDITING
            and not other_editing_workbaskets
        ):
            self.stdout.write(
                self.style.ERROR(
                    f"Error: Transitioning WorkBasket {workbasket.pk} from "
                    "EDITING status would leave no WorkBaskets in EDITING "
                    "status - an invalid state.",
                ),
            )
            self.stdout.write("Exiting.")
            exit(1)

        workbasket.status = options["STATUS"]
        workbasket.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"WorkBaskets {workbasket.pk} status now set to {workbasket.status}",
            ),
        )
        self.output_workbasket(workbasket)
