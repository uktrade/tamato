from typing import List

from django.conf import settings
from django.core.paginator import Paginator


def build_pagination_list(
    current_page: int,
    max_page: int,
    num_end_pages: int = 3,
) -> List[str]:
    """
    Builds a list of numbers for pagination, potentially including the first /
    last few pages.

    Returns:
    A list of ranges for the current_page, along with the the end pages if specified,
    broken up by ellipsis if they are not within 1 of each other.

    For example:

    >>> build_pagination_list(current_page=7, max_pages=12, num_end_pages=3)
    [1,2,3,"...",6,7,8,"...",10,11,12]
    """

    last_added = 0
    pages = []
    for page in range(1, max_page + 1):
        is_end_page = page <= num_end_pages or page > max_page - num_end_pages
        in_current_range = current_page - 1 <= page <= current_page + 1

        if is_end_page or in_current_range:
            if page != last_added + 1:
                pages.append("...")
            pages.append(str(page))
            last_added = page

    return pages


class LimitedPaginator(Paginator):
    """
    Provides a paginator with limited results for list views.

    The django `Paginator` has a `count` property,
    used for the sole purpose of determining the number of pages.
    Per django documentation, in some cases `Paginator.count`
    may trigger very inefficient database queries that include outer joins.

    In TaMato, some list views, such as Find and Edit Measures,
    can include a very long object list (millions of records)
    in addition to a large number of outer joins to all sorts of related entities.
    The resulting database query is extremely inefficient.

    The limited paginator imposes a limit beyond which
    the Paginator count will simply be set to a fixed number,
    while still providing the true count for smaller result sets
    (in order to avoid empty pages and inaccurate user feedback).

    For example, if the limit is set to 200,
    the count will be set at 200 for result sets with 300 objects,
    but the true count will be fetched for result sets with 100 objects.

    The max_count attribute is sent using a config variable in django settings.
    """

    max_count = settings.LIMITED_PAGINATOR_MAX_COUNT

    @property
    def limit_breached(self):
        """If the number of paginated objects breaches the
        LIMITED_PAGINATOR_MAX_COUNT, then return True, otherwise False."""
        try:
            self.object_list[self.max_count]
            return True
        except IndexError:
            return False

    @property
    def count(self):
        """Return the precise number of paginated objects up to
        LIMITED_PAGINATOR_MAX_COUNT, or LIMITED_PAGINATOR_MAX_COUNT if that
        limit is breached (use `limit_breached` property to establish whether
        the limit value has been breached and therefore returned)."""

        if self.limit_breached:
            return self.max_count
        else:
            return super().count
