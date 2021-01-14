import pytest

from common.pagination import build_pagination_list


@pytest.mark.parametrize(
    "current_page, total_pages, expected_result",
    [
        (1, 1, ["1"]),
        (1, 2, ["1", "2"]),
        (2, 3, ["1", "2", "3"]),
        (1, 3, ["1", "2", "3"]),
        (1, 10, ["1", "2", "3", "...", "8", "9", "10"]),
        (5, 12, ["1", "2", "3", "4", "5", "6", "...", "10", "11", "12"]),
        (8, 12, ["1", "2", "3", "...", "7", "8", "9", "10", "11", "12"]),
        (7, 12, ["1", "2", "3", "...", "6", "7", "8", "...", "10", "11", "12"]),
        (12, 12, ["1", "2", "3", "...", "10", "11", "12"]),
    ],
)
def test_pagination_provides_correct_object(current_page, total_pages, expected_result):
    result = build_pagination_list(current_page, total_pages)
    assert result == expected_result
