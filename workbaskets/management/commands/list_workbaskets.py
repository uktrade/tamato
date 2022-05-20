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

    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        workbaskets = WorkBasket.objects.all()
        if options["status"]:
            workbaskets = workbaskets.filter(status__in=options["status"])

        for w in workbaskets:
            self.stdout.write(f"WorkBasket {w}:")
            self.output_workbasket(w)
