from exporter.util import exceptions_as_messages
from exporter.util import item_timer


def test_exceptions_as_messages():
    exception_list = {
        "first_exception": [Exception("test")],
        "second_exception": [Exception("test2")],
    }

    messages = exceptions_as_messages(exception_list)

    assert messages == {
        "first_exception": ["raised an test"],
        "second_exception": ["raised an test2"],
    }


def test_item_timer():
    """Verify that item_timer yields a tuple containing the time to retrieve
    each item and the item itself."""
    items = item_timer([1, 2])

    time_taken, item = next(items)

    assert item == 1
    assert isinstance(time_taken, float)
    assert time_taken >= 0.0

    time_taken, item = next(items)

    assert item == 2
    assert isinstance(time_taken, float)
    assert time_taken >= 0.0
