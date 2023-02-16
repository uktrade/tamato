import logging
from typing import Any
from typing import Optional

from django.core.exceptions import ObjectDoesNotExist
from django.core.management import BaseCommand
from django.core.management.base import CommandParser

from checks.models import TrackedModelCheck
from workbaskets.management.util import WorkBasketCommandMixin

logger = logging.getLogger(__name__)


class Command(WorkBasketCommandMixin, BaseCommand):
    help = (
        "Update the 'successful' attribute on a TrackedModelCheck instance "
        "to True. As a precaution against inadvertently changing valid "
        "failures, this command attempts to ensure a failed check was "
        "not caused by a business rule failure. The command should still "
        "be applied with caution."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("WORKBASKET_ID", type=int)
        parser.add_argument("MODEL_CHECK_ID", type=int)

    def handle(self, *args: Any, **options: Any) -> Optional[str]:
        model_check = self.validate(
            int(options["MODEL_CHECK_ID"]),
            int(options["WORKBASKET_ID"]),
        )
        self.override_check_successful(model_check)

    def validate(self, model_check_id, workbasket_id):
        """Perform precautionary validation checks."""

        try:
            model_check = TrackedModelCheck.objects.get(pk=model_check_id)
        except ObjectDoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    f"Model check {model_check_id} not found. Exiting.",
                ),
            )
            exit(1)

        if model_check.successful:
            self.stdout.write(
                self.style.ERROR(
                    f"Model check {model_check_id} successful={model_check.successful}. "
                    f"Nothing to do. Exiting.",
                ),
            )
            exit(1)

        if not model_check.message or not model_check.message.startswith(
            "An internal error occurred",
        ):
            self.stdout.write(
                self.style.ERROR(
                    f"Model check {model_check_id} appears to be a valid error. "
                    f"Exiting.",
                ),
            )
            exit(1)

        workbasket = self.get_workbasket_or_exit(workbasket_id)
        if model_check.transaction_check.transaction.workbasket != workbasket:
            self.stdout.write(
                self.style.ERROR(
                    f"Model check {model_check_id} is not associated with workbasket {workbasket_id}",
                ),
            )
            exit(1)

        return model_check

    def override_check_successful(self, model_check):
        """Override `model_check.successful` to True and, if no other
        TrackedModelCheck instances on the parent TransactionCheck have a
        `successful` attribute value of False, then also set
        model_check.transaction_check.successful to True."""

        tranx_check = model_check.transaction_check

        self.stdout.write(f"Initial check values:")
        self.output_check_summary(model_check, tranx_check)

        model_check.successful = True
        model_check.save()

        bad_m_checks_on_t_check = TrackedModelCheck.objects.filter(
            transaction_check=tranx_check,
            successful=False,
        )
        if bad_m_checks_on_t_check:
            self.stdout.write("Done:")
            self.output_check_summary(model_check, tranx_check)
            self.stdout.write(
                f"{bad_m_checks_on_t_check.count()} unsuccessful model checks "
                f"remaining on related transaction check, {tranx_check.pk}",
            )
            exit(0)

        tranx_check.successful = True
        tranx_check.save()

        # Refresh for certainty.
        model_check.refresh_from_db()
        tranx_check.refresh_from_db()

        self.stdout.write("Done:")
        self.output_check_summary(model_check, tranx_check)

    def output_check_summary(self, model_check, tranx_check, indent_count=4):
        spaces = " " * indent_count
        self.stdout.write(
            f"{spaces}model_check({model_check.pk}).successful = {model_check.successful}",
        )
        self.stdout.write(
            f"{spaces}model_check({model_check.pk}).tranx_check({tranx_check.pk}).successful = {tranx_check.successful}",
        )
