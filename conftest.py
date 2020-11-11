from datetime import datetime
from datetime import timezone
from typing import Any
from typing import Dict
from typing import Type
from typing import Union

import pytest
from django.core.exceptions import ValidationError
from factory.django import DjangoModelFactory
from lxml import etree
from psycopg2.extras import DateTimeTZRange
from pytest_bdd import given
from rest_framework.test import APIClient

from common.models import TrackedModel
from common.serializers import TrackedModelSerializer
from common.tests import factories
from common.tests.util import Dates
from common.tests.util import generate_test_import_xml
from common.validators import UpdateType
from importer.management.commands.import_taric import import_taric
from workbaskets.validators import WorkflowStatus


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
    return factories.TransactionFactory.create().workbasket


@pytest.fixture
def unapproved_workbasket():
    return factories.WorkBasketFactory.create()


@pytest.fixture
def unique_identifying_fields():
    """Provides a function for checking a model of the specified factory class cannot be
    created with the same identifying_fields as an existing instance.

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
    """Provides a function for checking a model's foreign key link instance must exist.

    Usage:
        assert must_exist("field_name", LinkedModelFactory, ModelFactory)
    """
    # TODO drop the `dependency_name` argument, as with validity_period_contained

    def check(dependency_name, dependent_factory):
        non_existent_id = -1

        with pytest.raises(ValidationError):
            dependent_factory.create(
                **{f"{dependency_name}_id": non_existent_id},
            )

        return True

    return check


@pytest.fixture
def validity_period_contained(date_ranges):
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
            valid_between=date_ranges.starts_with_normal
        )

        try:
            dependent_factory.create(
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
def imported_fields_match(valid_user):
    """Provides a function for checking a model can be imported correctly.

    The function takes the following parameters:
        model: A model instance, or a factory class used to build the model.
            This model should not already exist in the database.
        serializer: An optional serializer class to convert the model to its TARIC XML
            representation. If not provided, the function attempts to use a serializer
            class named after the model, eg measures.serializers.<model-class-name>Serializer

    The function serializes the model to TARIC XML, inputs this to the importer, then
    fetches the newly created model from the database and compares the fields.

    It returns True if there are no discrepancies, allowing it to be used with `assert`.
    """

    def check(
        model: Union[TrackedModel, Type[DjangoModelFactory]],
        serializer: Type[TrackedModelSerializer],
    ) -> TrackedModel:
        if isinstance(model, type) and issubclass(model, DjangoModelFactory):
            model = model.build(update_type=UpdateType.CREATE)

        assert isinstance(
            model, TrackedModel
        ), "Either a factory or an object instance needs to be provided"

        xml = generate_test_import_xml(
            serializer(model, context={"format": "xml"}).data
        )

        import_taric(
            xml,
            valid_user.username,
            WorkflowStatus.PUBLISHED,
        )

        db_kwargs = {field: getattr(model, field) for field in model.identifying_fields}

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


@pytest.fixture(params=[UpdateType.UPDATE, UpdateType.DELETE])
def update_imported_fields_match(
    imported_fields_match,
    date_ranges,
    request,
):
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
                    dependency_model, DjangoModelFactory
                ):
                    kwargs[name] = dependency_model.create()
                else:
                    kwargs[name] = dependency_model

            if validity:
                kwargs["valid_between"] = validity[0]

            parent_model = model.create(**kwargs)

            kwargs.update(
                {
                    field: getattr(parent_model, field)
                    for field in parent_model.identifying_fields
                }
            )
            if validity:
                kwargs["valid_between"] = validity[1]

            model = model.build(
                update_type=update_type,
                **kwargs,
            )
        elif not parent_model:
            raise ValueError("parent_model must be defined if an instance is provided")

        updated_model = imported_fields_match(
            model,
            serializer,
        )

        version_group = parent_model.version_group
        version_group.refresh_from_db()
        assert version_group.versions.count() == 2
        assert version_group == updated_model.version_group
        assert version_group.current_version == updated_model
        assert version_group.current_version.update_type == update_type
        return updated_model

    return check
