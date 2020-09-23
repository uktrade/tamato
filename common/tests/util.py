import contextlib
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from io import StringIO
from typing import Any
from typing import Dict
from typing import Type

import pytest
from dateutil.relativedelta import relativedelta
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.urls import reverse
from factory.django import DjangoModelFactory
from lxml import etree
from psycopg2._range import DateTimeTZRange

from common.models import TrackedModel
from common.renderers import counter_generator
from common.serializers import TrackedModelSerializer
from common.validators import UpdateType
from importer.management.commands.import_taric import import_taric
from workbaskets.validators import WorkflowStatus

COMMODITIES_IMPLEMENTED = False
EXPORT_REFUND_NOMENCLATURE_IMPLEMENTED = False
INTERDEPENDENT_EXPORT_IMPLEMENTED = False
MEASURES_IMPLEMENTED = True
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

requires_interdependent_export = pytest.mark.skipif(
    not INTERDEPENDENT_EXPORT_IMPLEMENTED,
    reason="Interdependent exports not implemented",
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


NOW = datetime.now(tz=UTC).replace(hour=0, minute=0, second=0, microsecond=0)


class Dates:
    normal = DateTimeTZRange(
        NOW,
        NOW + relativedelta(months=+1),
    )
    earlier = DateTimeTZRange(
        NOW + relativedelta(years=-1),
        NOW + relativedelta(years=-1, months=+1),
    )
    later = DateTimeTZRange(
        NOW + relativedelta(years=+1, months=+1, days=+1),
        NOW + relativedelta(years=+1, months=+2),
    )
    big = DateTimeTZRange(
        NOW + relativedelta(years=-2),
        NOW + relativedelta(years=+2, days=+1),
    )
    adjacent_earlier = DateTimeTZRange(
        NOW + relativedelta(months=-1),
        NOW,
    )
    adjacent_later = DateTimeTZRange(
        NOW + relativedelta(months=+1),
        NOW + relativedelta(months=+2),
    )
    adjacent_even_later = DateTimeTZRange(
        NOW + relativedelta(months=+2, days=+1),
        NOW + relativedelta(months=+3),
    )
    adjacent_later_big = DateTimeTZRange(
        NOW + relativedelta(months=+1),
        NOW + relativedelta(years=+2, months=+2),
    )
    overlap_normal = DateTimeTZRange(
        NOW + relativedelta(days=+14),
        NOW + relativedelta(days=+14, months=+1, years=+1),
    )
    overlap_normal_earlier = DateTimeTZRange(
        NOW + relativedelta(months=-1, days=+14),
        NOW + relativedelta(days=+14),
    )
    overlap_big = DateTimeTZRange(
        NOW + relativedelta(years=+1),
        NOW + relativedelta(years=+3, days=+2),
    )
    after_big = DateTimeTZRange(
        NOW + relativedelta(years=+3, months=+1),
        NOW + relativedelta(years=+3, months=+2),
    )
    backwards = DateTimeTZRange(
        NOW + relativedelta(months=+1),
        NOW + relativedelta(days=+1),
    )
    starts_with_normal = DateTimeTZRange(
        NOW,
        NOW + relativedelta(days=+14),
    )
    ends_with_normal = DateTimeTZRange(
        NOW + relativedelta(days=+14),
        NOW + relativedelta(months=+1),
    )
    current = DateTimeTZRange(
        NOW + relativedelta(weeks=-4),
        NOW + relativedelta(weeks=+4),
    )
    future = DateTimeTZRange(
        NOW + relativedelta(weeks=+10),
        NOW + relativedelta(weeks=+20),
    )
    no_end = DateTimeTZRange(NOW, None)
    normal_first_half = DateTimeTZRange(
        NOW,
        NOW + relativedelta(days=+14),
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
