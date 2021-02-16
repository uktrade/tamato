from typing import List


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
