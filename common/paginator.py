from django.conf import settings
from django.core.paginator import Paginator


class LimitedPaginator(Paginator):
    """
    Provides a paginator with limited results for list views.

    The django `Paginator` has a `count` property,
    used for the sole purpose of determining the number of pages.
    Per django documentation, in some cases `Paginator.count`
    may trigger very inefficient database queries that include outer joins.

    In TaMato, some list views, such as Find and Edit Measures,
    can include a very long object list (millions of rows)
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
    def count(self):
        try:
            self.object_list[self.max_count]
            return self.max_count
        except IndexError:
            return super().count
