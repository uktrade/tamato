import contextlib
from datetime import datetime

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


@pytest.mark.skip()
def test_fo4():
    """At least one description record is mandatory. the start date of the first
    description period must be equal to the start date of the footnote. no two
    associated description periods may have the same start date. the start date must be
    less than or equal to the end date of the footnote.
    """
    pass


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
        ("2020-05-18", "2020-05-20", False),
        ("2020-05-18", "2020-05-19", False),
        ("2020-05-19", "2020-05-20", False),
        ("2020-05-17", "2020-05-20", True),
        ("2020-05-18", "2020-05-21", True),
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
            datetime.fromisoformat("2020-05-18"), datetime.fromisoformat("2020-05-21"),
        ),
    )

    with raises_if(django.core.exceptions.ValidationError, expected):
        f = factories.FootnoteFactory.build(
            footnote_type=t,
            valid_between=DateTimeTZRange(
                datetime.fromisoformat(start), datetime.fromisoformat(end),
            ),
        )
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
