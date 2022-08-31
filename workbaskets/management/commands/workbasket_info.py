import logging
from typing import Any
from typing import Optional

from django.core.management import BaseCommand
from django.core.management.base import CommandParser

from workbaskets.management.util import WorkBasketCommandMixin
from workbaskets.models import WorkBasket

logger = logging.getLogger(__name__)


class Command(WorkBasketCommandMixin, BaseCommand):
    help = "Get the current info, including check status, of a workbasket."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("WORKBASKET_PK", type=int)

    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        workbasket = WorkBasket.objects.get(
            pk=int(options["WORKBASKET_PK"]),
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"WorkBaskets {workbasket.pk} status {workbasket.status}",
            ),
        )
        self.output_workbasket(workbasket)
