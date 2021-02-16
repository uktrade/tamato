from workbaskets.models import WorkBasket


class WithCurrentWorkBasket:
    """Add models in the current workbasket to the modelview queryset."""

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.with_workbasket(WorkBasket.current(self.request))
