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
    help = (
        "Show clashes for a given measure, if any exist. If no --workbasket "
        "parameter is supplied then only the most recent (last) measure "
        "instance is checked for clashes. Supplying the --workbasket parameter "
        "ensures that all CREATE and UPDATE instances in the workbasket are "
        "checked for clashes."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("MEASURE_SID", type=int)
        parser.add_argument(
            "--workbasket-pk",
            type=int,
            help=("Check all instances of the meausre in the given workbasket."),
        )

    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        sid = int(options["MEASURE_SID"])
        workbasket_info = ""

        if options["workbasket_pk"]:
            workbasket = self.get_workbasket_or_exit(
                int(options["workbasket_pk"]),
            )
            measures = list(
                Measure.objects.filter(
                    sid=sid,
                    transaction__workbasket=workbasket,
                ),
            )
            workbasket_info = f" in workbasket.pk={workbasket.pk}"
        else:
            measures = [
                Measure.objects.filter(sid=sid).order_by("transaction").last(),
            ]

        if not measures:
            self.stderr.write(
                self.style.ERROR(f"measure sid={sid} not found."),
            )
            exit(1)

        self.stdout.write(
            f"Checking {len(measures)} measure instance(s)" f"{workbasket_info}.",
        )

        for measure in measures:
            me32 = ME32(measure.transaction)
            clashes = me32.clashing_measures(measure)

            self.stdout.write(
                self.style.SUCCESS(
                    f"Measure:  "
                    f"sid={sid},  "
                    f"update_type={measure.get_update_type_display()},  "
                    f"effective_valid_between={measure.effective_valid_between}  "
                    f"transaction.id={measure.transaction.id}  "
                    f"workbasket.pk={measure.transaction.workbasket.pk}, ",
                ),
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"  having the attached commodity:  "
                    f"item_id={measure.goods_nomenclature.item_id},  "
                    f"sid={measure.goods_nomenclature.sid},  "
                    f"valid_between={measure.goods_nomenclature.valid_between}, ",
                ),
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"    with Indents:",
                ),
            )
            for indent in measure.goods_nomenclature.indents.all():
                self.stdout.write(
                    self.style.SUCCESS(
                        f"      sid={indent.sid},  "
                        f"indent={indent.indent},  "
                        f"valid_start={indent.validity_start}, "
                        f"version_group={indent.version_group.pk}, ",
                    ),
                )

            if clashes:
                self.stdout.write(f"{clashes.count()} ME32 rule clashe(s) found:")
                for c in clashes:
                    self.stdout.write(
                        self.style.ERROR(
                            f"Measure:  "
                            f"sid={c.sid},  "
                            f"update_type={c.get_update_type_display()},  "
                            f"effective_valid_between={c.effective_valid_between}  "
                            f"transaction.id={c.transaction.id},  "
                            f"workbasket.pk={c.transaction.workbasket.pk}, ",
                        ),
                    )
                    # NOTE: Is this commodity the latest as at measure tranx?
                    self.stdout.write(
                        self.style.ERROR(
                            f"  having the attached Commodity:  "
                            f"item_id={c.goods_nomenclature.item_id},  "
                            f"sid={c.goods_nomenclature.sid},  "
                            f"valid_between={c.goods_nomenclature.valid_between}, ",
                        ),
                    )
                    self.stdout.write(
                        self.style.ERROR(
                            f"  with Indents:",
                        ),
                    )
                    for indent in c.goods_nomenclature.indents.all():
                        self.stdout.write(
                            self.style.ERROR(
                                f"    sid={indent.sid},  "
                                f"indent={indent.indent},  "
                                f"validity_start={indent.validity_start}, "
                                f"version_group={indent.version_group.pk}, ",
                            ),
                        )

                    self.stdout.write()
