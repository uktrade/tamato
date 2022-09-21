import logging
from typing import Any
from typing import Optional

from django.core.management import BaseCommand
from django.core.management.base import CommandParser

from measures.business_rules import ME32
from measures.models import Measure
from workbaskets.management.util import WorkBasketCommandMixin

logger = logging.getLogger(__name__)


class Command(WorkBasketCommandMixin, BaseCommand):
    help = "Show clashes for a given measure, if any exist."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("MEASURE_SID", type=int)

    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        sid = int(options["MEASURE_SID"])
        measure = Measure.objects.filter(sid=sid).order_by("transaction").last()
        if not measure:
            self.stderr.write(
                self.style.ERROR(f"measure sid={sid} not found."),
            )
            exit(1)

        me32 = ME32(measure.transaction)
        clashes = me32.clashing_measures(measure)

        self.stdout.write(
            self.style.SUCCESS(
                f"{clashes.count()} ME32 rule clashe(s) against " f"Measure.sid={sid}.",
            ),
        )
        if clashes:
            self.stdout.write("Clashes:")
            for c in clashes:
                self.stdout.write(
                    self.style.ERROR(
                        self.stdout.write(f"     Measure.sid={c.sid}"),
                    ),
                )
