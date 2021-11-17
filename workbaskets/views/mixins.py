from workbaskets.models import WorkBasket


class WithCurrentWorkBasket:
    """Add models in the current workbasket to the modelview queryset."""

    def get_queryset(self):
        qs = super().get_queryset()
        transaction = None
        current = WorkBasket.current(self.request)
        if current:
            transaction = current.transactions.last()

        return qs.approved_up_to_transaction(transaction)
