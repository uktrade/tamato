from django.views.generic import ListView

from packaging.models import COMPLETED_PACKAGING_STATES
from packaging.models import PackagedWorkBasket


class WorkBasketPackagingQueue(ListView):
    """UI endpoint for viewing and filtering workbaskets."""

    model = PackagedWorkBasket
    template_name = "packaging/packaging_queue.jinja"

    def get_queryset(self):
        return PackagedWorkBasket.objects.filter(
            state__in=COMPLETED_PACKAGING_STATES,
        )

    def post(self):
        # TODO
        pass
