import contextlib
from datetime import datetime
from datetime import timedelta
from datetime import timezone

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse
from lxml import etree
from psycopg2._range import DateTimeTZRange


COMMODITIES_IMPLEMENTED = False
MEASURES_IMPLEMENTED = False
MEURSING_TABLES_IMPLEMENTED = False

requires_commodities = pytest.mark.skipif(
    not COMMODITIES_IMPLEMENTED, reason="Commodities not implemented",
)

requires_measures = pytest.mark.skipif(
    not MEASURES_IMPLEMENTED, reason="Measures not implemented",
)

requires_meursing_tables = pytest.mark.skipif(
    not MEURSING_TABLES_IMPLEMENTED, reason="Meursing tables not implemented",
)


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


def check_validator(validate, value, expected_valid):
    try:
        validate(value)
    except ValidationError:
        if expected_valid:
            pytest.fail(f'Unexpected validation error for value "{value}"')
    except Exception:
        raise
    else:
        if not expected_valid:
            pytest.fail(f'Expected validation error for value "{value}"')


def validate_taric_xml(factory):
    def decorator(func):
        def wraps(api_client, taric_schema, approved_workbasket, *args, **kwargs):
            factory.create(workbasket=approved_workbasket)
            response = api_client.get(
                reverse("workbasket-detail", kwargs={"pk": approved_workbasket.pk}),
                {"format": "xml"},
            )

            assert response.status_code == 200

            xml = etree.XML(response.content)

            taric_schema.validate(xml)

            assert not taric_schema.error_log, f"XML errors: {taric_schema.error_log}"

            func(
                api_client, taric_schema, approved_workbasket, *args, xml=xml, **kwargs
            )

        return wraps

    return decorator


class Dates:
    normal = DateTimeTZRange(
        datetime(2021, 1, 1, tzinfo=timezone.utc),
        datetime(2021, 2, 1, tzinfo=timezone.utc),
    )
    earlier = DateTimeTZRange(
        datetime(2020, 1, 1, tzinfo=timezone.utc),
        datetime(2020, 2, 1, tzinfo=timezone.utc),
    )
    later = DateTimeTZRange(
        datetime(2022, 2, 2, tzinfo=timezone.utc),
        datetime(2022, 3, 1, tzinfo=timezone.utc),
    )
    big = DateTimeTZRange(
        datetime(2019, 1, 1, tzinfo=timezone.utc),
        datetime(2023, 1, 2, tzinfo=timezone.utc),
    )
    adjacent_earlier = DateTimeTZRange(
        datetime(2020, 12, 1, tzinfo=timezone.utc),
        datetime(2020, 12, 31, tzinfo=timezone.utc),
    )
    adjacent_later = DateTimeTZRange(
        datetime(2022, 2, 1, tzinfo=timezone.utc),
        datetime(2022, 3, 1, tzinfo=timezone.utc),
    )
    overlap_normal = DateTimeTZRange(
        datetime(2021, 1, 15, tzinfo=timezone.utc),
        datetime(2022, 2, 15, tzinfo=timezone.utc),
    )
    overlap_normal_earlier = DateTimeTZRange(
        datetime(2020, 12, 15, tzinfo=timezone.utc),
        datetime(2021, 1, 15, tzinfo=timezone.utc),
    )
    overlap_big = DateTimeTZRange(
        datetime(2022, 1, 1, tzinfo=timezone.utc),
        datetime(2024, 1, 3, tzinfo=timezone.utc),
    )
    after_big = DateTimeTZRange(
        datetime(2024, 2, 1, tzinfo=timezone.utc),
        datetime(2024, 3, 1, tzinfo=timezone.utc),
    )
    backwards = DateTimeTZRange(
        datetime(2021, 2, 1, tzinfo=timezone.utc),
        datetime(2021, 1, 2, tzinfo=timezone.utc),
    )
    starts_with_normal = DateTimeTZRange(
        datetime(2021, 1, 1, tzinfo=timezone.utc),
        datetime(2021, 1, 15, tzinfo=timezone.utc),
    )
    ends_with_normal = DateTimeTZRange(
        datetime(2021, 1, 15, tzinfo=timezone.utc),
        datetime(2021, 2, 1, tzinfo=timezone.utc),
    )
    current = DateTimeTZRange(
        datetime.today() - timedelta(weeks=4), datetime.today() + timedelta(weeks=4)
    )
    future = DateTimeTZRange(
        datetime.today() + timedelta(weeks=10), datetime.today() + timedelta(weeks=20),
    )
    no_end = DateTimeTZRange(datetime(2021, 1, 1, tzinfo=timezone.utc), None)
    normal_first_half = DateTimeTZRange(
        datetime(2021, 1, 1, tzinfo=timezone.utc),
        datetime(2021, 1, 15, tzinfo=timezone.utc),
    )
