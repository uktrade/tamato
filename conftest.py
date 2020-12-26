import contextlib
from datetime import datetime
from datetime import timezone
from functools import lru_cache
from typing import Any
from typing import Callable
from typing import Optional
from unittest.mock import patch
from unittest.mock import PropertyMock

import boto3
import pytest
from django.conf import settings
from django.core.exceptions import ValidationError
from lxml import etree
from moto import mock_s3
from psycopg2.extras import DateTimeTZRange
from pytest_bdd import given
from rest_framework.test import APIClient

from common.tests import factories
from common.tests.util import Dates
from common.util import get_field_tuple
from common.validators import UpdateType
from exporter.storages import HMRCStorage


def pytest_addoption(parser):
    parser.addoption(
        "--hmrc-live-api",
        action="store_true",
        help="Test will call the live HMRC Sandbox API and not mock the request.",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "hmrc_live_api: mark test calling the live HMRC Sandbox API"
    )


def pytest_runtest_setup(item):
    if "hmrc_live_api" in item.keywords and not item.config.getoption(
        "--hmrc-live-api"
    ):
        pytest.skip("Not calling live HMRC Sandbox API. Use --hmrc-live-api to do so.")


@pytest.fixture(scope="session")
def celery_config():
    return {
        "broker_url": "memory://",
        "result_backend": "cache",
        "task_always_eager": True,
    }


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
        DateTimeTZRange(
            datetime.fromisoformat(start).replace(tzinfo=timezone.utc),
            datetime.fromisoformat(end).replace(tzinfo=timezone.utc),
        ),
        expect_error,
    )


@pytest.fixture
def date_ranges() -> Dates:
    return Dates()


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def valid_user(db):
    return factories.UserFactory.create()


@given('a valid user named "Alice"', target_fixture="a_valid_user_called_alice")
def a_valid_user_called_alice():
    return factories.UserFactory.create(username="Alice")


@pytest.fixture
def valid_user_login(client, valid_user):
    client.force_login(valid_user)


@given("I am logged in as Alice", target_fixture="alice_login")
def alice_login(client, a_valid_user_called_alice):
    client.force_login(a_valid_user_called_alice)


@pytest.fixture
def valid_user_api_client(api_client, valid_user) -> APIClient:
    api_client.force_login(valid_user)
    return api_client


@pytest.fixture
def taric_schema(settings) -> etree.XMLSchema:
    with open(settings.TARIC_XSD) as xsd_file:
        return etree.XMLSchema(etree.parse(xsd_file))


@pytest.fixture
def approved_workbasket():
    return factories.ApprovedWorkBasketFactory.create()


@pytest.fixture
def approved_transaction():
    return factories.ApprovedTransactionFactory.create()


@pytest.fixture
def workbasket():
    return factories.WorkBasketFactory.create()


@pytest.fixture
def unique_identifying_fields(approved_workbasket):
    """Provides a function for checking a model of the specified factory class cannot be
    created with the same identifying_fields as an existing instance.

    Usage:
        assert unique_identifying_fields(FactoryClass)
    """

    # TODO allow factory or model instance as argument

    def check(factory):
        existing = factory(workbasket=approved_workbasket)

        with pytest.raises(ValidationError):
            duplicate = factory(
                valid_between=existing.valid_between,
                **{
                    field: getattr(existing, field)
                    for field in factory._meta.model.identifying_fields
                },
            )

        return True

    return check


@pytest.fixture
def must_exist(approved_workbasket):
    """Provides a function for checking a model's foreign key link instance must exist.

    Usage:
        assert must_exist("field_name", LinkedModelFactory, ModelFactory)
    """

    # TODO drop the `dependency_name` argument, as with validity_period_contained

    def check(dependency_name, dependency_factory, dependent_factory):
        dependency = dependency_factory.create(workbasket=approved_workbasket)
        non_existent_id = dependency.pk
        dependency.delete()

        with pytest.raises(ValidationError):
            dependent_factory.create(
                **{f"{dependency_name}_id": non_existent_id},
            )

        return True

    return check


@pytest.fixture
def validity_period_contained(date_ranges, approved_workbasket):
    """Provides a function for checking a model's validity period must be contained
    within the validity period of the specified model.

    Usage:
        assert validity_period_contained("field_name", ContainerModelFactory, ContainedModelFactory)
    """

    # TODO drop the `dependency_name` argument, inspect the model for a ForeignKey to
    # the specified container model. Add `field_name` kwarg for disambiguation if
    # multiple ForeignKeys.

    def check(dependency_name, dependency_factory, dependent_factory):
        dependency = dependency_factory.create(
            workbasket=approved_workbasket, valid_between=date_ranges.starts_with_normal
        )

        try:
            dependent = dependent_factory.create(
                valid_between=date_ranges.normal,
                **{dependency_name: dependency},
            )

        except ValidationError:
            pass

        except Exception as exc:
            raise

        else:
            pytest.fail(
                f"{dependency_factory._meta.get_model_class().__name__} validity must "
                f"span {dependent_factory._meta.get_model_class().__name__} validity."
            )

        return True

    return check


@pytest.fixture
def s3():
    with mock_s3():
        s3 = boto3.client("s3")
        yield s3


@pytest.fixture
def s3_object_exists(s3):
    """Provide a function to verify that a particular object exists in
    an expected bucket.
    """

    def check(bucket_name, key):
        bucket_names = [
            bucket_info["Name"] for bucket_info in s3.list_buckets()["Buckets"]
        ]
        if not bucket_names:
            return False

        object_names = [
            contents["Key"]
            for contents in s3.list_objects(Bucket=bucket_name)["Contents"]
        ]
        return key in object_names

    return check


@pytest.fixture
def hmrc_storage():
    """Patch HMRCStorage with moto so that nothing is really uploaded to s3"""
    with mock_s3():
        storage = HMRCStorage()
        session = boto3.session.Session()

        with patch(
            "storages.backends.s3boto3.S3Boto3Storage.connection",
            new_callable=PropertyMock,
        ) as mock_connection_property, patch(
            "storages.backends.s3boto3.S3Boto3Storage.bucket",
            new_callable=PropertyMock,
        ) as mock_bucket_property:
            # By default Motos mock_s3 doesn't stop S3Boto3Storage from connection to s3.
            # Patch the connection and bucket properties on it to use Moto instead.
            @lru_cache(None)
            def get_connection():
                return session.resource("s3")

            @lru_cache(None)
            def get_bucket():
                connection = get_connection()
                connection.create_bucket(
                    Bucket=settings.HMRC_STORAGE_BUCKET_NAME,
                    CreateBucketConfiguration={
                        "LocationConstraint": settings.AWS_S3_REGION_NAME
                    },
                )

                bucket = connection.Bucket(settings.HMRC_STORAGE_BUCKET_NAME)
                return bucket

            mock_connection_property.side_effect = get_connection
            mock_bucket_property.side_effect = get_bucket
            yield storage


@pytest.fixture
def make_duplicate_record():
    """Provides a function for making a duplicate record to test a UniqueIdentifyingFields BusinessRule."""

    def make_dupe(factory, identifying_fields=None):
        existing = factory.create()

        # allow overriding identifying_fields
        if identifying_fields is None:
            identifying_fields = list(factory._meta.model.identifying_fields)

            if hasattr(existing, "valid_between"):
                identifying_fields.append("valid_between")

        return factory.create(
            **dict(get_field_tuple(existing, field) for field in identifying_fields)
        )

    return make_dupe


@pytest.fixture
def delete_record():
    """Provides a function for deleting a record."""

    def delete(model):
        return model.new_draft(
            factories.WorkBasketFactory(),
            update_type=UpdateType.DELETE,
        )

    return delete


@pytest.fixture
def reference_nonexistent_record():
    """Provides a context manager for creating a record with a reference to a
    non-existent record to test a MustExist BusinessRule.
    """

    @contextlib.contextmanager
    def make_record(
        factory,
        reference_field_name: str,
        teardown: Optional[Callable[[Any], Any]] = None,
    ):
        # XXX relies on private API
        dependency_factory = factory._meta.declarations[
            reference_field_name
        ].get_factory()

        dependency = dependency_factory.create()
        non_existent_id = dependency.pk
        if teardown:
            teardown(dependency)
        else:
            dependency.delete()

        record = factory.create(**{f"{reference_field_name}_id": non_existent_id})

        try:
            yield record
        finally:
            record.delete()

    return make_record
