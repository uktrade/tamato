import contextlib
from datetime import datetime
from datetime import timedelta
from datetime import timezone

import django
import pytest
from psycopg2.extras import DateTimeTZRange

from common.tests import factories
from footnotes import models


pytestmark = pytest.mark.django_db


@contextlib.contextmanager
def raises_if(exception, expected):
    try:
        yield
    except exception:
        if not expected:
            raise
    else:
        if expected:
            pytest.fail(f"Did not raise {exception}")


@pytest.fixture(
    params=[
        ("2020-05-18", "2020-05-17", True),
        ("2020-05-18", "2020-05-18", False),
        ("2020-05-18", "2020-05-19", False),
    ]
)
def validity_range(request):
    start, end, expect_error = request.param
    return (
        DateTimeTZRange(datetime.fromisoformat(start), datetime.fromisoformat(end),),
        expect_error,
    )


def test_fot1():
    """The type of the footnote must be unique"""
    factories.FootnoteTypeFactory.create(footnote_type_id="AA")

    with pytest.raises(django.db.utils.IntegrityError):
        factories.FootnoteTypeFactory.create(footnote_type_id="AA")


def test_fot2():
    """The footnote type cannot be deleted if it is used in a footnote"""
    t = factories.FootnoteTypeFactory.create(footnote_type_id="AA")
    factories.FootnoteFactory.create(footnote_type=t)

    with pytest.raises(django.db.utils.IntegrityError):
        t.delete()


def test_fot3(validity_range):
    """The start date must be less than or equal to the end date"""
    range, expected = validity_range
    with raises_if(django.db.utils.DataError, expected):
        factories.FootnoteTypeFactory.create(valid_between=range)


def test_fo1():
    """The referenced footnote type must exist."""
    non_existent = 999

    # ensure footnote type does not exist
    try:
        models.FootnoteType.objects.get(pk=non_existent).delete()
    except models.FootnoteType.DoesNotExist:
        pass

    with pytest.raises(django.db.utils.IntegrityError):
        footnote = factories.FootnoteFactory.create(footnote_type_id=non_existent)
        django.db.connections["default"].check_constraints()


def test_fo2():
    """The combination footnote type and code must be unique."""
    t = factories.FootnoteTypeFactory.create(footnote_type_id="AA")
    factories.FootnoteFactory.create(footnote_id="000", footnote_type=t)

    with pytest.raises(django.db.utils.IntegrityError):
        factories.FootnoteFactory.create(footnote_id="000", footnote_type=t)


def test_fo3(validity_range):
    """The start date must be less than or equal to the end date"""
    range, expected = validity_range
    with raises_if(django.db.utils.DataError, expected):
        factories.FootnoteFactory.create(valid_between=range)


def test_fo4_no_descriptions():
    """At least one description record is mandatory."""
    footnote = factories.FootnoteFactory.create()
    with pytest.raises(django.core.exceptions.ValidationError):
        footnote.full_clean()


@pytest.mark.parametrize(
    "description_starts, expect_error",
    [
        (["2020-05-01", "2020-05-11"], True),
        (["2020-05-11", "2020-05-21"], False),
        (["2020-05-21", "2020-05-31"], True),
    ],
    ids=[
        "first-description-starts-before-footnote",
        "first-description-starts-equal-to-footnote",
        "first-description-starts-after-footnote",
    ],
)
def test_fo4_first_description_starts_at_same_time(description_starts, expect_error):
    """The start date of the first description period must be equal to the start date of
    the footnote.
    """
    footnote_validity = DateTimeTZRange(
        datetime.fromisoformat("2020-05-11").replace(tzinfo=timezone.utc),
        datetime.fromisoformat("2020-05-21").replace(tzinfo=timezone.utc),
    )
    ft = factories.FootnoteTypeFactory.create(valid_between=footnote_validity,)
    footnote = factories.FootnoteFactory.create(
        footnote_type=ft, valid_between=footnote_validity,
    )
    for start in description_starts:
        start = datetime.fromisoformat(start).replace(tzinfo=timezone.utc)
        end = start + timedelta(days=10)
        factories.FootnoteDescriptionFactory.create(
            footnote=footnote, valid_between=DateTimeTZRange(start, end),
        )
    with raises_if(django.core.exceptions.ValidationError, expect_error):
        footnote.full_clean()


@pytest.mark.parametrize(
    "description_starts, expect_error",
    [(["2020-05-01", "2020-05-01"], True), (["2020-05-01", "2020-05-11"], False),],
)
def test_fo4_descriptions_starts_unique(description_starts, expect_error):
    """No two associated description periods may have the same start date."""
    footnote = factories.FootnoteFactory.create()
    with raises_if(django.db.utils.IntegrityError, expect_error):
        for start in description_starts:
            factories.FootnoteDescriptionFactory.create(
                footnote=footnote,
                valid_between=DateTimeTZRange(
                    datetime.fromisoformat(start), datetime(2020, 5, 31),
                ),
            )


@pytest.mark.parametrize(
    "footnote_end, description_start, expect_error",
    [("2020-05-21", "2020-05-01", False), ("2020-05-21", "2020-06-01", True),],
)
def test_fo4_description_start_before_footnote_end(
    footnote_end, description_start, expect_error
):
    """The start date must be less than or equal to the end date of the footnote.
    """
    f_end = datetime.fromisoformat(footnote_end).replace(tzinfo=timezone.utc)
    d_start = datetime.fromisoformat(description_start).replace(tzinfo=timezone.utc)
    footnote = factories.FootnoteFactory.create(
        valid_between=DateTimeTZRange(f_end - timedelta(days=30), f_end)
    )
    with raises_if(django.core.exceptions.ValidationError, expect_error):
        desc = factories.FootnoteDescriptionFactory.create(
            footnote=footnote,
            valid_between=DateTimeTZRange(d_start, d_start + timedelta(days=10)),
        )
        desc.full_clean()


@pytest.mark.skip(reason="Measures not implemented")
def test_fo5():
    """When a footnote is used in a measure the validity period of the footnote must
    span the validity period of the measure.
    """
    pass


@pytest.mark.skip(reason="Nomenclature not implemented")
def test_fo6():
    """When a footnote is used in a goods nomenclature the validity period of the
    footnote must span the validity period of the association with the goods
    nomenclature.
    """
    pass


@pytest.mark.skip(reason="Nomenclature not implemented")
def test_fo7():
    """When a footnote is used in an export refund nomenclature code the validity period
    of the footnote must span the validity period of the association with the export
    refund code.
    """
    pass


@pytest.mark.skip(reason="Additional codes not implemented")
def test_fo9():
    """When a footnote is used in an additional code the validity period of the footnote
    must span the validity period of the association with the additional code.
    """
    pass


@pytest.mark.skip(reason="Meursing tables not implemented")
def test_fo10():
    """When a footnote is used in a meursing table heading the validity period of the
    footnote must span the validity period of the association with the meursing heading.
    """
    pass


@pytest.mark.parametrize(
    "start, end, expected",
    [
        ("2020-05-18", "2020-05-19", False),
        ("2020-05-18", "2020-05-20", False),
        ("2020-05-18", "2020-05-21", False),
        ("2020-05-19", "2020-05-20", False),
        ("2020-05-17", "2020-05-20", True),
        ("2020-05-16", "2020-05-17", True),
        ("2020-05-22", "2020-05-23", True),
    ],
)
def test_fo17(start, end, expected):
    """The validity period of the footnote type must span the validity period of the
    footnote.
    """
    t = factories.FootnoteTypeFactory.create(
        footnote_type_id="AA",
        valid_between=DateTimeTZRange(
            datetime.fromisoformat("2020-05-18").replace(tzinfo=timezone.utc),
            datetime.fromisoformat("2020-05-21").replace(tzinfo=timezone.utc),
        ),
    )

    with raises_if(django.core.exceptions.ValidationError, expected):
        range = DateTimeTZRange(
            datetime.fromisoformat(start).replace(tzinfo=timezone.utc),
            datetime.fromisoformat(end).replace(tzinfo=timezone.utc),
        )
        f = factories.FootnoteFactory(footnote_type=t, valid_between=range)
        fd = factories.FootnoteDescriptionFactory(footnote=f, valid_between=range)
        f.full_clean()


@pytest.mark.skip(reason="Measures not implemented")
def test_fo11():
    """When a footnote is used in a measure then the footnote may not be deleted."""
    pass


@pytest.mark.skip(reason="Nomenclature not implemented")
def test_fo12():
    """When a footnote is used in a goods nomenclature then the footnote may not be
    deleted.
    """
    pass


@pytest.mark.skip(reason="Nomenclature not implemented")
def test_fo13():
    """When a footnote is used in an export refund code then the footnote may not be
    deleted.
    """
    pass


@pytest.mark.skip(reason="Additional codes not implemented")
def test_fo15():
    """When a footnote is used in an additional code then the footnote may not be
    deleted.
    """
    pass


@pytest.mark.skip(reason="Meursing tables not implemented")
def test_fo16():
    """When a footnote is used in a meursing table heading then the footnote may not be
    deleted.
    """
    pass
