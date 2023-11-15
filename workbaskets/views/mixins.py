from workbaskets.models import WorkBasket


class WithCurrentWorkBasket:
    """Add models in the current workbasket to the modelview queryset."""

    @property
    def workbasket(self) -> WorkBasket:
        return WorkBasket.current(self.request)

    def get_queryset(self):
        qs = super().get_queryset()

        return qs.current()
