import pytest

from common.tests import factories

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("old_dates", "old_terminating_reg", "new_dates", "expect_any", "expect_same"),
    (
        ("no_end", lambda: None, "normal", True, False),
        ("normal", factories.RegulationFactory, "no_end", False, False),
        ("normal", factories.RegulationFactory, "normal", True, True),
    ),
)
def test_terminating_regulation_update(
    old_dates,
    old_terminating_reg,
    new_dates,
    expect_any,
    expect_same,
):
    """Tests that when the validity dates on a measure are changed, a
    terminating regulation is automatically added or removed, and that any
    existing terminating regulation is used."""
    regulation = old_terminating_reg()
    instance = factories.MeasureFactory.create(
        valid_between=factories.date_ranges(old_dates),
        terminating_regulation=regulation,
    )
    new_version = instance.new_version(
        instance.transaction.workbasket,
        valid_between=factories.date_ranges(new_dates).function(),
    )
    assert (new_version.terminating_regulation is not None) == expect_any
    assert (new_version.terminating_regulation == regulation) == expect_same
