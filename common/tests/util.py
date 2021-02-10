import contextlib
from datetime import date
from datetime import datetime
from datetime import timezone
from functools import wraps
from io import BytesIO
from itertools import count
from typing import Any
from typing import Dict
from typing import Type

import pytest
from dateutil.parser import parse as parse_date
from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.urls import reverse
from factory.django import DjangoModelFactory
from freezegun import freeze_time
from lxml import etree

from common.models import TrackedModel
from common.renderers import counter_generator
from common.serializers import TrackedModelSerializer
from common.util import TaricDateRange
from common.validators import UpdateType
from importer.management.commands.import_taric import import_taric
from workbaskets.validators import WorkflowStatus

INTERDEPENDENT_IMPORT_IMPLEMENTED = True
UPDATE_IMPORTER_IMPLEMENTED = False
EXPORT_REFUND_NOMENCLATURE_IMPLEMENTED = False
COMMODITIES_IMPLEMENTED = True
MEURSING_TABLES_IMPLEMENTED = False
PARTIAL_TEMPORARY_STOP_IMPLEMENTED = False
UTC = timezone.utc

requires_commodities = pytest.mark.skipif(
    not COMMODITIES_IMPLEMENTED,
    reason="Commodities not implemented",
)

requires_export_refund_nomenclature = pytest.mark.skipif(
    not EXPORT_REFUND_NOMENCLATURE_IMPLEMENTED,
    reason="Export refund nomenclature not implemented",
)

requires_meursing_tables = pytest.mark.skipif(
    not MEURSING_TABLES_IMPLEMENTED,
    reason="Meursing tables not implemented",
)

requires_partial_temporary_stop = pytest.mark.skipif(
    not PARTIAL_TEMPORARY_STOP_IMPLEMENTED,
    reason="Partial temporary stop not implemented",
)

requires_interdependent_import = pytest.mark.skipif(
    not INTERDEPENDENT_IMPORT_IMPLEMENTED,
    reason="Interdependent imports not implemented",
)

requires_update_importer = pytest.mark.skipif(
    not UPDATE_IMPORTER_IMPLEMENTED,
    reason="Requires Updating importers to be implemented",
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


_transaction_counter = count(start=1)


def generate_test_import_xml(obj: dict) -> BytesIO:

    xml = render_to_string(
        template_name="workbaskets/taric/transaction_detail.xml",
        context={
            "envelope_id": next(_transaction_counter),
            "tracked_models": [obj],
            "transaction_id": next(_transaction_counter),
            "message_counter": counter_generator(),
            "counter_generator": counter_generator,
        },
    )

    return BytesIO(xml.encode())


def validate_taric_xml_record_order(xml):
    """Raise AssertionError if any record codes are not in order."""
    last_code = "00000"
    for record in xml.findall(".//record", namespaces=xml.nsmap):
        record_code = record.findtext(".//record.code", namespaces=xml.nsmap)
        subrecord_code = record.findtext(".//subrecord.code", namespaces=xml.nsmap)
        full_code = record_code + subrecord_code
        if full_code < last_code:
            raise AssertionError(
                f"Elements out of order in XML: {last_code}, {full_code}"
            )
        last_code = full_code


def taric_xml_record_codes(xml):
    """Yields tuples of (record_code, subrecord_code)"""
    return [
        (
            record.findtext(".//record.code", namespaces=xml.nsmap),
            record.findtext(".//subrecord.code", namespaces=xml.nsmap),
        )
        for record in xml.findall(".//record", namespaces=xml.nsmap)
    ]


def validate_taric_xml(
    factory=None, instance=None, factory_kwargs=None, check_order=True
):
    def decorator(func):
        def wraps(
            api_client,
            taric_schema,
            approved_transaction,
            valid_user,
            *args,
            **kwargs,
        ):
            if not factory and not instance:
                raise AssertionError(
                    "Either a factory or an object instance need to be provided"
                )
            if factory and instance:
                raise AssertionError(
                    "Either a factory or an object instance need to be provided - not both."
                )

            current_instance = instance or factory.create(
                transaction=approved_transaction, **factory_kwargs or {}
            )

            api_client.force_login(user=valid_user)
            response = api_client.get(
                reverse(
                    "workbasket-detail",
                    kwargs={"pk": approved_transaction.workbasket.pk},
                ),
                {"format": "xml"},
            )

            assert response.status_code == 200

            content = response.content

            xml = etree.XML(content)

            taric_schema.validate(xml)

            assert not taric_schema.error_log, f"XML errors: {taric_schema.error_log}"

            if check_order:
                validate_taric_xml_record_order(xml)

            args = (
                api_client,
                taric_schema,
                approved_transaction,
                *args,
            )
            kwargs = {"xml": xml, **kwargs}

            func(
                *args,
                **kwargs,
            )

        return wraps

    return decorator


def validate_taric_import(
    serializer: Type[TrackedModelSerializer],
    factory: DjangoModelFactory = None,
    instance: TrackedModel = None,
    update_type: int = UpdateType.CREATE.value,
    factory_kwargs: Dict[str, Any] = None,
    dependencies: Dict[str, Type[DjangoModelFactory]] = None,
):
    def decorator(func):
        def wraps(valid_user, *args, **kwargs):
            if not factory and not instance:
                raise AssertionError(
                    "Either a factory or an object instance need to be provided"
                )
            if factory and instance:
                raise AssertionError(
                    "Either a factory or an object instance need to be provided - not both."
                )

            _factory_kwargs = factory_kwargs or {}
            _factory_kwargs.update(
                **{
                    name: dependency_factory.create()
                    for name, dependency_factory in (
                        dependencies.items() if dependencies else {}.items()
                    )
                }
            )

            test_object = (
                instance
                if instance
                else factory.build(update_type=update_type, **(_factory_kwargs or {}))
            )

            xml = generate_test_import_xml(
                serializer(test_object, context={"format": "xml"}).data
            )

            import_taric(xml, valid_user.username, WorkflowStatus.PUBLISHED.value)

            model = instance.__class__ if instance else factory._meta.model

            db_kwargs = {
                field: getattr(test_object, field) for field in model.identifying_fields
            }
            db_object = model.objects.get_latest_version(**db_kwargs)

            func(
                valid_user,
                *args,
                test_object=test_object,
                db_object=db_object,
                **kwargs,
            )

        return wraps

    return decorator


class Dates:
    deltas = {
        "normal": (relativedelta(), relativedelta(months=+1)),
        "earlier": (relativedelta(years=-1), relativedelta(years=-1, months=+1)),
        "later": (
            relativedelta(years=+1, months=+1, days=+1),
            relativedelta(years=+1, months=+2),
        ),
        "big": (relativedelta(years=-2), relativedelta(years=+2, days=+1)),
        "adjacent_earlier": (relativedelta(months=-1), relativedelta(days=-1)),
        "adjacent_later": (relativedelta(months=+1, days=+1), relativedelta(months=+2)),
        "adjacent_no_end": (relativedelta(months=+1, days=+1), None),
        "adjacent_even_later": (
            relativedelta(months=+2, days=+1),
            relativedelta(months=+3),
        ),
        "adjacent_earlier_big": (
            relativedelta(years=-2, months=-2),
            relativedelta(years=-2),
        ),
        "adjacent_later_big": (
            relativedelta(months=+1, days=+1),
            relativedelta(years=+2, months=+2),
        ),
        "overlap_normal": (
            relativedelta(days=+15),
            relativedelta(days=+14, months=+1, years=+1),
        ),
        "overlap_normal_earlier": (
            relativedelta(months=-1, days=+14),
            relativedelta(days=+14),
        ),
        "overlap_big": (relativedelta(years=+1), relativedelta(years=+3, days=+2)),
        "after_big": (
            relativedelta(years=+3, months=+1),
            relativedelta(years=+3, months=+2),
        ),
        "backwards": (relativedelta(months=+1), relativedelta(days=+1)),
        "starts_with_normal": (relativedelta(), relativedelta(days=+14)),
        "ends_with_normal": (relativedelta(days=+14), relativedelta(months=+1)),
        "current": (relativedelta(weeks=-4), relativedelta(weeks=+4)),
        "future": (relativedelta(weeks=+10), relativedelta(weeks=+20)),
        "no_end": (relativedelta(), None),
        "normal_first_half": (relativedelta(), relativedelta(days=+14)),
    }

    @property
    def now(self):
        return self.datetime_now.date()

    @property
    def datetime_now(self):
        return datetime.now(tz=UTC).replace(hour=0, minute=0, second=0, microsecond=0)

    def __getattr__(self, name):
        if name in self.deltas:
            start, end = self.deltas[name]
            start = self.now + start
            if end is not None:
                end = self.now + end
            return TaricDateRange(start, end)
        raise AttributeError(name)

    @classmethod
    def short_before(cls, dt):
        return TaricDateRange(
            dt + relativedelta(months=-1),
            dt + relativedelta(days=-14),
        )

    @classmethod
    def medium_before(cls, dt):
        return TaricDateRange(
            dt + relativedelta(months=-1),
            dt + relativedelta(days=-1),
        )

    @classmethod
    def short_after(cls, dt):
        return TaricDateRange(
            dt + relativedelta(days=+14),
            dt + relativedelta(months=+1),
        )

    @classmethod
    def short_overlap(cls, dt):
        return TaricDateRange(
            dt + relativedelta(months=-1),
            dt + relativedelta(months=+1),
        )

    @classmethod
    def no_end_before(cls, dt):
        return TaricDateRange(
            dt + relativedelta(months=-1),
            None,
        )


def only_applicable_after(cutoff):
    """Decorator which asserts that a test fails after a specified cutoff date.

    :param cutoff: A date string, or datetime object before which the test should fail.
    """

    cutoff = parse_date(cutoff)

    def decorator(fn):
        @wraps(fn)
        def do_test(*args, **kwargs):
            # test should pass normally
            fn(*args, **kwargs)

            # test should fail before cutoff
            with freeze_time(cutoff + relativedelta(days=-1)):
                try:
                    fn(*args, **kwargs)

                except pytest.fail.Exception:
                    pass

                except Exception:
                    raise

                else:
                    pytest.fail(f"Rule applied before {cutoff:%Y-%m-%d}")

            return True

        return do_test

    return decorator
