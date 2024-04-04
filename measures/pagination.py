from django.conf import settings
from django.utils.functional import cached_property

from common.pagination import LimitedPaginator


class MeasurePaginator(LimitedPaginator):
    """
    Provides a paginator with limited results for measure list views.

    For details on limited paginators, please see the docs for the base class.

    The max_count attribute is sent using a config variable in django settings.
    """

    max_count = settings.MEASURES_PAGINATOR_MAX_COUNT

    @cached_property
    def count(self):
        """Override `LimitedPaginator.count` to avoid performing slow `.count()`
        operations on measure querysets chained with the filter
        `.with_effective_valid_between()`."""

        if self.limit_breached:
            return self.max_count
        else:
            return len(self.object_list)
