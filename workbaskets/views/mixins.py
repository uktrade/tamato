from workbaskets.models import WorkBasket


class WithCurrentWorkBasket:
    """Add models in the current workbasket to the modelview queryset."""

    @property
    def workbasket(self) -> WorkBasket:
        return WorkBasket.current(self.request)

    def get_queryset(self):
        qs = super().get_queryset()
        transaction = None
        current = self.workbasket
        if current:
            transaction = current.transactions.last()

        return qs.approved_up_to_transaction(transaction)

    def get_context_data(self, *args, **kwargs):
        return super().get_context_data(workbasket=self.workbasket, *args, **kwargs)
