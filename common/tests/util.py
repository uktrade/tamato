import contextlib
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from functools import wraps
from io import StringIO
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
from psycopg2._range import DateTimeTZRange

from common.models import TrackedModel
from common.renderers import counter_generator
from common.serializers import TrackedModelSerializer
from common.validators import UpdateType
from importer.management.commands.import_taric import import_taric
from workbaskets.validators import WorkflowStatus

INTERDEPENDENT_IMPORT_IMPLEMENTED = True
UPDATE_IMPORTER_IMPLEMENTED = False
EXPORT_REFUND_NOMENCLATURE_IMPLEMENTED = False
MEASURES_IMPLEMENTED = True
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

requires_measures = pytest.mark.skipif(
    not MEASURES_IMPLEMENTED,
    reason="Measures not implemented",
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


def generate_test_import_xml(obj: dict) -> StringIO:
    xml = render_to_string(
        template_name="workbaskets/taric/transaction_detail.xml",
        context={
            "tracked_models": [obj],
            "transaction_id": 1,
            "message_counter": counter_generator(),
            "counter_generator": counter_generator,
        },
    )

    return StringIO(xml)


def validate_taric_xml(factory=None, instance=None, factory_kwargs=None):
    def decorator(func):
        def wraps(api_client, taric_schema, approved_workbasket, *args, **kwargs):
            if not factory and not instance:
                raise AssertionError(
                    "Either a factory or an object instance need to be provided"
                )
            if factory and instance:
                raise AssertionError(
                    "Either a factory or an object instance need to be provided - not both."
                )

            if not instance:
                factory(workbasket=approved_workbasket, **factory_kwargs or {})

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
    @property
    def now(self):
        return datetime.now(tz=UTC).replace(hour=0, minute=0, second=0, microsecond=0)

    @property
    def normal(self):
        return DateTimeTZRange(
            self.now,
            self.now + relativedelta(months=+1),
        )

    @property
    def earlier(self):
        return DateTimeTZRange(
            self.now + relativedelta(years=-1),
            self.now + relativedelta(years=-1, months=+1),
        )

    @property
    def later(self):
        return DateTimeTZRange(
            self.now + relativedelta(years=+1, months=+1, days=+1),
            self.now + relativedelta(years=+1, months=+2),
        )

    @property
    def big(self):
        return DateTimeTZRange(
            self.now + relativedelta(years=-2),
            self.now + relativedelta(years=+2, days=+1),
        )

    @property
    def adjacent_earlier(self):
        return DateTimeTZRange(
            self.now + relativedelta(months=-1),
            self.now,
        )

    @property
    def adjacent_later(self):
        return DateTimeTZRange(
            self.now + relativedelta(months=+1),
            self.now + relativedelta(months=+2),
        )

    @property
    def adjacent_even_later(self):
        return DateTimeTZRange(
            self.now + relativedelta(months=+2, days=+1),
            self.now + relativedelta(months=+3),
        )

    @property
    def adjacent_later_big(self):
        return DateTimeTZRange(
            self.now + relativedelta(months=+1),
            self.now + relativedelta(years=+2, months=+2),
        )

    @property
    def overlap_normal(self):
        return DateTimeTZRange(
            self.now + relativedelta(days=+14),
            self.now + relativedelta(days=+14, months=+1, years=+1),
        )

    @property
    def overlap_normal_earlier(self):
        return DateTimeTZRange(
            self.now + relativedelta(months=-1, days=+14),
            self.now + relativedelta(days=+14),
        )

    @property
    def overlap_big(self):
        return DateTimeTZRange(
            self.now + relativedelta(years=+1),
            self.now + relativedelta(years=+3, days=+2),
        )

    @property
    def after_big(self):
        return DateTimeTZRange(
            self.now + relativedelta(years=+3, months=+1),
            self.now + relativedelta(years=+3, months=+2),
        )

    @property
    def backwards(self):
        return DateTimeTZRange(
            self.now + relativedelta(months=+1),
            self.now + relativedelta(days=+1),
        )

    @property
    def starts_with_normal(self):
        return DateTimeTZRange(
            self.now,
            self.now + relativedelta(days=+14),
        )

    @property
    def ends_with_normal(self):
        return DateTimeTZRange(
            self.now + relativedelta(days=+14),
            self.now + relativedelta(months=+1),
        )

    @property
    def current(self):
        return DateTimeTZRange(
            self.now + relativedelta(weeks=-4),
            self.now + relativedelta(weeks=+4),
        )

    @property
    def future(self):
        return DateTimeTZRange(
            self.now + relativedelta(weeks=+10),
            self.now + relativedelta(weeks=+20),
        )

    @property
    def no_end(self):
        return DateTimeTZRange(
            self.now,
            None,
        )

    @property
    def normal_first_half(self):
        return DateTimeTZRange(
            self.now,
            self.now + relativedelta(days=+14),
        )

    @classmethod
    def short_before(cls, dt):
        return DateTimeTZRange(
            dt + relativedelta(months=-1),
            dt + relativedelta(days=-14),
        )

    @classmethod
    def medium_before(cls, dt):
        return DateTimeTZRange(
            dt + relativedelta(months=-1),
            dt + relativedelta(days=-1),
        )

    @classmethod
    def no_end_before(cls, dt):
        return DateTimeTZRange(
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
                    pytest.fail(f"Rule applied before {cutoff:%d/%m/%Y}")

            return True

        return do_test

    return decorator
