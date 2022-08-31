import enum

from workbaskets.models import WorkBasket


class WorkBasketOutputFormat(enum.Enum):
    READABLE = 1
    COMPACT = 2


def first_line_of(s: str) -> str:
    """Return the first line of a string."""
    return s.lstrip().partition("\n")[0]


class WorkBasketCommandMixin:
    def _output_workbasket_readable(
        self, workbasket, show_transaction_info, indent=4, **kwargs
    ):
        spaces = " " * indent
        self.stdout.write(f"WorkBasket {workbasket}:")
        self.stdout.write(f"{spaces}pk: {workbasket.pk}")
        self.stdout.write(f"{spaces}title: {first_line_of(workbasket.title)}")
        self.stdout.write(f"{spaces}reason: {first_line_of(workbasket.reason)}")
        self.stdout.write(f"{spaces}status: {workbasket.status}")
        self.stdout.write(
            f"{spaces}unchecked or errors: {workbasket.unchecked_or_errored_transactions.exists()}",
        )
        self.stdout.write(
            f"{spaces}tracked model count: {workbasket.tracked_models.count()}",
        )
        if show_transaction_info:
            self.stdout.write(
                f"{spaces}transactions: {workbasket.transactions.first().pk} - {workbasket.transactions.last().pk}",
            )

    def _output_workbasket_compact(self, workbasket, show_transaction_info, **kwargs):
        self.stdout.write(
            f"{workbasket.pk}, {first_line_of(workbasket.title)}, "
            f"{first_line_of(workbasket.reason) or '-'}, {workbasket.status}, "
            f"{workbasket.unchecked_or_errored_transactions}, "
            f"{workbasket.tracked_models.count()}",
            ending="" if show_transaction_info else "\n",
        )
        if show_transaction_info:
            self.stdout.write(
                f", {workbasket.transactions.first().pk} - {workbasket.transactions.last().pk}",
            )

    def output_workbasket(
        self,
        workbasket,
        show_transaction_info=False,
        output_format=WorkBasketOutputFormat.READABLE,
        **kwargs,
    ):
        if output_format == WorkBasketOutputFormat.COMPACT:
            self._output_workbasket_compact(workbasket, show_transaction_info, **kwargs)
        else:
            self._output_workbasket_readable(
                workbasket, show_transaction_info, **kwargs
            )

    def output_workbaskets(self, workbaskets, show_transaction_info, output_format):
        """
        Output a list of workbaskets.

        :param workbaskets: Sequence of workbaskets to output.
        :param output_format: Output format, value of WorkBasketOutputFormat Enum.
        :param show_transaction_info: Whether to show first / this is slower.
        """
        if output_format == WorkBasketOutputFormat.COMPACT:
            self.stdout.write(
                "pk, title, reason, status",
                ending="" if show_transaction_info else "\n",
            )
            if show_transaction_info:
                self.stdout.write(", transactions")

        for w in workbaskets:
            self.output_workbasket(w, show_transaction_info, output_format)

    def get_workbasket_or_exit(self, workbasket_pk):
        """
        Get the workbasket instance by its primary key, workbasket_pk.

        If no matching workbasket is found, then output an error message and
        exit the process.
        """
        try:
            return WorkBasket.objects.get(
                pk=workbasket_pk,
            )
        except WorkBasket.DoesNotExist:
            self.stderr.write(
                self.style.ERROR(f"Workbasket pk={workbasket_pk} not found."),
            )
            exit(1)
