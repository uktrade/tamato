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
    help = (
        "Set up the currently 'active' WorkBasket. The given WorkBasket "
        "must have status 'ARCHIVED' or 'EDITING'. All other WorkBaskets that "
        "currently have their status set to 'EDITING' before this command is "
        "exectuted will be transitioned to 'ARCHIVED'."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("WORKBASKET_PK", type=int)

    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        new_workbasket = WorkBasket.objects.get(
            pk=int(options["WORKBASKET_PK"]),
        )
        if (
            new_workbasket.status != WorkflowStatus.ARCHIVED
            and new_workbasket.status != WorkflowStatus.EDITING
        ):
            self.stdout.write(
                f"WorkBasket {new_workbasket.pk} must have status of ARCHIVED or EDITING.",
            )
            self.output_workbasket(new_workbasket)
            exit(0)

        old_workbaskets = WorkBasket.objects.filter(
            status=WorkflowStatus.EDITING,
        ).exclude(pk=new_workbasket.pk)

        new_workbasket.status = WorkflowStatus.EDITING
        new_workbasket.save()

        self.stdout.write(
            f"WorkBaskets {new_workbasket.pk} now in EDITING status:",
        )
        self.output_workbasket(new_workbasket)

        # Bulk update doesn't call WorkBasket.save(), so iterate and save for
        # safety and control.
        if old_workbaskets:
            for w in old_workbaskets:
                w.status = WorkflowStatus.ARCHIVED
                w.save()
                self.stdout.write(
                    f"Transitioned WorkBasket {w.pk} to ARCHIVED status:",
                )
                self.output_workbasket(w)
        else:
            self.stdout.write(
                f"No WorkBaskets transitioned to ARCHIVED status.",
            )
