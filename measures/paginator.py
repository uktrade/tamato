from django.conf import settings

from common.paginator import LimitedPaginator


class MeasurePaginator(LimitedPaginator):
    """
    Provides a paginator with limited results for measure list views.

    For details on limited paginators, please see the docs for the base class.

    The max_count attribute is sent using a config variable in django settings.
    """

    max_count = settings.LIMITED_PAGINATOR_MAX_COUNT
