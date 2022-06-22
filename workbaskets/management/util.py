import enum


class WorkBasketOutputFormat(enum.Enum):
    READABLE = 1
    COMPACT = 2


def first_line_of(s: str) -> str:
    """Return the first line of a string."""
    return s.lstrip().partition("\n")[0]


class WorkBasketCommandMixin:
    def get_transaction_span(self, transactions):
        """
        Return a string representing the span from first to last transaction.

        Hyphens are output if there are no transactions.
        """
        first_tx = transactions.first().pk if transactions else None
        last_tx = transactions.last().pk if transactions else None
        return f"{first_tx or '-'} - {last_tx or '-'}"

    def _output_workbasket_readable(
        self, workbasket, show_transaction_info, indent=4, **kwargs
    ):
        spaces = " " * indent
        self.stdout.write(f"WorkBasket {workbasket}:")
        self.stdout.write(f"{spaces}pk: {workbasket.pk}")
        self.stdout.write(f"{spaces}title: {first_line_of(workbasket.title)}")
        self.stdout.write(f"{spaces}reason: {first_line_of(workbasket.reason)}")
        self.stdout.write(f"{spaces}status: {workbasket.status}")
        if show_transaction_info:
            self.stdout.write(
                f"{spaces}transactions: "
                + self.get_transaction_span(workbasket.transactions),
            )

    def _output_workbasket_compact(self, workbasket, show_transaction_info, **kwargs):
        self.stdout.write(
            f"{workbasket.pk}, {first_line_of(workbasket.title)}, {first_line_of(workbasket.reason) or '-'}, {workbasket.status}",
            ending="" if show_transaction_info else "\n",
        )
        if show_transaction_info:
            self.stdout.write(
                ", " + self.get_transaction_span(workbasket.transactions),
            )

    def output_workbasket(
        self,
        workbasket,
        show_transaction_info,
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
