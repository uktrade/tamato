import contextlib
from datetime import date
from functools import lru_cache
from typing import Any
from typing import Callable
from typing import Dict
from typing import Optional
from typing import Type
from typing import Union
from unittest.mock import PropertyMock
from unittest.mock import patch

import boto3
import pytest
from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ValidationError
from factory.django import DjangoModelFactory
from lxml import etree
from moto import mock_s3
from pytest_bdd import given
from rest_framework.test import APIClient

from common.models import TrackedModel
from common.serializers import TrackedModelSerializer
from common.tests import factories
from common.tests.util import Dates
from common.tests.util import generate_test_import_xml
from common.util import TaricDateRange
from common.util import get_field_tuple
from common.validators import UpdateType
from exporter.storages import HMRCStorage
from importer.nursery import get_nursery
from importer.taric import process_taric_xml_stream
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus


def pytest_addoption(parser):
    parser.addoption(
        "--hmrc-live-api",
        action="store_true",
        help="Test will call the live HMRC Sandbox API and not mock the request.",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "hmrc_live_api: mark test calling the live HMRC Sandbox API",
    )


def pytest_runtest_setup(item):
    if "hmrc_live_api" in item.keywords and not item.config.getoption(
        "--hmrc-live-api",
    ):
        pytest.skip("Not calling live HMRC Sandbox API. Use --hmrc-live-api to do so.")


def pytest_bdd_apply_tag(tag, function):
    if tag == "todo":
        marker = pytest.mark.skip(reason="Not implemented yet")
        marker(function)
        return True
    if tag == "xfail":
        marker = pytest.mark.xfail()
        marker(function)
        return True


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
    ],
)
def validity_range(request):
    start, end, expect_error = request.param
    return (
        TaricDateRange(
            date.fromisoformat(start),
            date.fromisoformat(end),
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
def policy_group(db) -> Group:
    policy_g = Group.objects.create()
    tracked_model_perm = Permission.objects.get(
        content_type__app_label="common",
        codename="add_trackedmodel",
    )
    add_workbasket_perm = Permission.objects.get(
        content_type__app_label="workbaskets",
        codename="add_workbasket",
    )
    change_workbasket_perm = Permission.objects.get(
        content_type__app_label="workbaskets",
        codename="change_workbasket",
    )
    policy_g.permissions.add(tracked_model_perm)
    policy_g.permissions.add(add_workbasket_perm)
    policy_g.permissions.add(change_workbasket_perm)
    return policy_g


@pytest.fixture
def valid_user(db, policy_group):
    user = factories.UserFactory.create()
    policy_group.user_set.add(user)
    return user


@given('a valid user named "Alice"', target_fixture="a_valid_user_called_alice")
def a_valid_user_called_alice():
    return factories.UserFactory.create(username="Alice")


@pytest.fixture
def valid_user_client(client, valid_user):
    client.force_login(valid_user)
    return client


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
def new_workbasket() -> WorkBasket:
    workbasket = factories.WorkBasketFactory.create(
        status=WorkflowStatus.NEW_IN_PROGRESS,
    )
    transaction = factories.TransactionFactory.create(workbasket=workbasket)
    with transaction:
        for _ in range(2):
            factories.FootnoteTypeFactory.create()

    return workbasket


@pytest.fixture
def approved_workbasket():
    return factories.ApprovedWorkBasketFactory.create()


@pytest.fixture
def approved_transaction():
    return factories.ApprovedTransactionFactory.create()


@pytest.fixture
def unapproved_transaction():
    return factories.UnapprovedTransactionFactory.create()


@pytest.fixture
def workbasket():
    return factories.WorkBasketFactory.create()


@pytest.fixture
def unique_identifying_fields():
    """
    Provides a function for checking a model of the specified factory class
    cannot be created with the same identifying_fields as an existing instance.

    Usage:
        assert unique_identifying_fields(FactoryClass)
    """

    # TODO allow factory or model instance as argument

    def check(factory):
        existing = factory()

        with pytest.raises(ValidationError):
            factory(
                valid_between=existing.valid_between,
                **{
                    field: getattr(existing, field)
                    for field in factory._meta.model.identifying_fields
                },
            )

        return True

    return check


@pytest.fixture
def must_exist():
    """
    Provides a function for checking a model's foreign key link instance must
    exist.

    Usage:
        assert must_exist("field_name", LinkedModelFactory, ModelFactory)
    """

    # TODO drop the `dependency_name` argument, as with validity_period_contained

    def check(dependency_name, dependent_factory):
        non_existent_id = -1

        with pytest.raises((ValidationError, ObjectDoesNotExist)):
            dependent_factory.create(
                **{f"{dependency_name}_id": non_existent_id},
            )

        return True

    return check


@pytest.fixture
def validity_period_contained(date_ranges):
    """
    Provides a function for checking a model's validity period must be contained
    within the validity period of the specified model.

    Usage:
        assert validity_period_contained("field_name", ContainerModelFactory, ContainedModelFactory)
    """

    # TODO drop the `dependency_name` argument, inspect the model for a ForeignKey to
    # the specified container model. Add `field_name` kwarg for disambiguation if
    # multiple ForeignKeys.

    def check(dependency_name, dependency_factory, dependent_factory):
        dependency = dependency_factory.create(
            valid_between=date_ranges.starts_with_normal,
        )

        try:
            dependent_factory.create(
                valid_between=date_ranges.normal,
                **{dependency_name: dependency},
            )

        except ValidationError:
            pass

        else:
            pytest.fail(
                f"{dependency_factory._meta.get_model_class().__name__} validity must "
                f"span {dependent_factory._meta.get_model_class().__name__} validity.",
            )

        return True

    return check


@pytest.fixture
def imported_fields_match(valid_user, settings):
    """
    Provides a function for checking a model can be imported correctly.

    The function takes the following parameters:
        model: A model instance, or a factory class used to build the model.
            This model should not already exist in the database.
        serializer: An optional serializer class to convert the model to its TARIC XML
            representation. If not provided, the function attempts to use a serializer
            class named after the model, eg measures.serializers.<model-class-name>Serializer

    The function serializes the model to TARIC XML, inputs this to the importer, then
    fetches the newly created model from the database and compares the fields.

    It returns the imported object if there are no discrepancies, allowing it to be
    further tested.
    """

    def check(
        model: Union[TrackedModel, Type[DjangoModelFactory]],
        serializer: Type[TrackedModelSerializer],
    ) -> TrackedModel:
        get_nursery().cache.clear()
        settings.SKIP_WORKBASKET_VALIDATION = True
        if isinstance(model, type) and issubclass(model, DjangoModelFactory):
            model = model.build(update_type=UpdateType.CREATE)

        assert isinstance(
            model,
            TrackedModel,
        ), "Either a factory or an object instance needs to be provided"

        xml = generate_test_import_xml(
            serializer(model, context={"format": "xml"}).data,
        )

        process_taric_xml_stream(
            xml,
            username=valid_user.username,
            status=WorkflowStatus.PUBLISHED,
        )

        db_kwargs = model.get_identifying_fields()
        imported = model.__class__.objects.get_latest_version(**db_kwargs)

        checked_fields = (
            set(field.name for field in imported._meta.fields)
            - set(field.name for field in TrackedModel._meta.fields)
            - {"trackedmodel_ptr"}
        )

        for field in checked_fields:
            imported_value = getattr(imported, field)
            source_value = getattr(model, field)
            assert (
                imported_value == source_value
            ), f"imported '{field}' ({imported_value} - {type(imported_value)}) does not match source '{field}' ({source_value} - {type(source_value)})"

        return imported

    return check


@pytest.fixture(params=(UpdateType.UPDATE, UpdateType.DELETE))
def update_imported_fields_match(
    imported_fields_match,
    date_ranges,
    request,
):
    """
    Provides much the same functionality as imported_fields_match, however makes
    some adjustments for updates and deletes.

    In addition to imported_fields_match a previously created object is
    generated. The data around version groups is also tested.
    """

    def check(
        model: Union[TrackedModel, Type[DjangoModelFactory]],
        serializer: Type[TrackedModelSerializer],
        parent_model: TrackedModel = None,
        dependencies: Dict[str, Union[TrackedModel, Type[DjangoModelFactory]]] = None,
        kwargs: Dict[str, Any] = None,
        validity=(date_ranges.normal, date_ranges.adjacent_no_end),
    ):
        update_type = request.param
        if isinstance(model, type) and issubclass(model, DjangoModelFactory):
            if parent_model:
                raise ValueError("Can't have parent_model and a factory defined")

            # Build kwargs and dependencies needed to make a complete model.
            # This can't rely on the factory itself as the dependencies need
            # to be in the database and .build does not save anything.
            kwargs = kwargs or {}
            for name, dependency_model in (dependencies or {}).items():
                if isinstance(dependency_model, type) and issubclass(
                    dependency_model,
                    DjangoModelFactory,
                ):
                    kwargs[name] = dependency_model.create()
                else:
                    kwargs[name] = dependency_model

            if validity:
                kwargs["valid_between"] = validity[0]

            parent_model = model.create(**kwargs)

            kwargs.update(parent_model.get_identifying_fields())
            if validity:
                kwargs["valid_between"] = validity[1]

            model = model.build(
                update_type=update_type,
                **kwargs,
            )
        elif not parent_model:
            raise ValueError("parent_model must be defined if an instance is provided")

        try:
            updated_model = imported_fields_match(
                model,
                serializer,
            )
        except model.__class__.DoesNotExist:
            if update_type == UpdateType.UPDATE:
                raise
            updated_model = model.__class__.objects.get(
                update_type=UpdateType.DELETE, **model.get_identifying_fields()
            )

        version_group = parent_model.version_group
        version_group.refresh_from_db()
        assert version_group.versions.count() == 2
        assert version_group == updated_model.version_group
        assert version_group.current_version == updated_model
        assert version_group.current_version.update_type == update_type
        return updated_model

    return check


@pytest.fixture
def s3():
    with mock_s3():
        s3 = boto3.client("s3")
        yield s3


@pytest.fixture
def s3_object_exists(s3):
    """Provide a function to verify that a particular object exists in an
    expected bucket."""

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
    """Patch HMRCStorage with moto so that nothing is really uploaded to s3."""
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
                        "LocationConstraint": settings.AWS_S3_REGION_NAME,
                    },
                )

                bucket = connection.Bucket(settings.HMRC_STORAGE_BUCKET_NAME)
                return bucket

            mock_connection_property.side_effect = get_connection
            mock_bucket_property.side_effect = get_bucket
            yield storage


@pytest.fixture
def make_duplicate_record():
    """Provides a function for making a duplicate record to test a
    UniqueIdentifyingFields BusinessRule."""

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
    non-existent record to test a MustExist BusinessRule."""

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
