import logging
from typing import Any
from typing import Optional

from django.core.management import BaseCommand
from django.core.management.base import CommandParser

from taric.models import Envelope

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "envelope_id",
            help="Envelope id [6 digit number], defaults to most recent envelope.",
            type=int,
            default=None,
            action="store",
            nargs="?",
        )
        parser.add_argument(
            "--list-envelopes",
            action="store_const",
            const=True,
            default=False,
        )

        return super().add_arguments(parser)

    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        if options["list_envelopes"]:
            for envelope in Envelope.objects.all():
                self.stdout.write(f"{envelope.envelope_id}")
        else:
            if options["envelope_id"] is None:
                envelope = Envelope.objects.last()
            else:
                envelope = Envelope.objects.get(envelope_id=options["envelope_id"])

            # TODO output sequences
