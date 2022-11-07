from __future__ import annotations

import contextlib
from dataclasses import dataclass
from functools import partial
from typing import Any
from typing import Callable
from typing import Dict
from typing import Optional
from typing import Sequence
from typing import Type
from unittest.mock import patch

import boto3
import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.test.client import RequestFactory
from django.test.html import parse_html
from django.urls import reverse
from factory.django import DjangoModelFactory
from lxml import etree
from moto import mock_s3
from pytest_bdd import given
from pytest_bdd import parsers
from pytest_bdd import then
from rest_framework.test import APIClient

from common.business_rules import BusinessRule
from common.business_rules import BusinessRuleViolation
from common.business_rules import UpdateValidity
from common.business_rules import ValidityPeriodContained
from common.models import TrackedModel
from common.models.transactions import Transaction
from common.models.transactions import TransactionPartition
from common.models.utils import override_current_transaction
from common.serializers import TrackedModelSerializer
from common.tests import factories
from common.tests.models import model_with_history
from common.tests.util import Dates
from common.tests.util import assert_records_match
from common.tests.util import export_workbasket
from common.tests.util import generate_test_import_xml
from common.tests.util import get_form_data
from common.tests.util import make_duplicate_record
from common.tests.util import make_non_duplicate_record
from common.tests.util import raises_if
from common.validators import UpdateType
from importer.nursery import get_nursery
from importer.taric import process_taric_xml_stream
from workbaskets.models import WorkBasket
from workbaskets.models import get_partition_scheme
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


@pytest.fixture(scope="session", autouse=True)
def celery_config():
    return {
        "broker_url": "memory://",
        "result_backend": "cache",
        "cache_backend": "memory",
        "task_always_eager": True,
    }


@pytest.fixture(
    params=(
        ("normal", "normal", True),
        ("normal", "overlap_normal", False),
        ("overlap_normal", "normal", False),
        ("big", "normal", True),
        ("later", "normal", False),
    ),
    ids=(
        "equal_dates",
        "overlaps_end",
        "overlaps_start",
        "contains",
        "no_overlap",
    ),
)
def spanning_dates(request, date_ranges):
    """Returns a pair of date ranges for a container object and a contained
    object, and a flag indicating whether the container date ranges completely
    spans the contained date range."""

    container_validity, contained_validity, container_spans_contained = request.param
    return (
        getattr(date_ranges, container_validity),
        getattr(date_ranges, contained_validity),
        container_spans_contained,
    )


@pytest.fixture
def assert_spanning_enforced(spanning_dates, update_type):
    """
    Provides a function that thoroughly checks if the validity period of a
    contained object is enforced to be within the validity period of a container
    object.

    In particular it also checks that the passed business rule doesn't take into
    account deleted contained items in its enforcement, and that it always uses
    the latest version of related objects.

    This is useful in implementing tests for business rules of the form:

        When a "contained object" is used in a "container object" the validity
        period of the "container object" must span the validity period of the
        "contained object".
    """

    def check(
        factory: Type[DjangoModelFactory],
        business_rule: Type[ValidityPeriodContained],
        **factory_kwargs,
    ):
        container_validity, contained_validity, fully_spanned = spanning_dates

        contained = getattr(business_rule, "contained_field_name") or ""
        container = getattr(business_rule, "container_field_name") or ""

        # If the test is checking an UPDATE or a DELETE, set the dates to be
        # valid on the original version so that we can tell if it is
        # successfully checking the later version.
        validity_on_contained = (
            container_validity
            if update_type != UpdateType.CREATE
            else contained_validity
        )

        object = factory.create(
            **factory_kwargs,
            **{
                f"{contained}{'__' if contained else ''}valid_between": validity_on_contained,
                f"{contained}{'__' if contained else ''}update_type": UpdateType.CREATE,
                f"{container}{'__' if container else ''}valid_between": container_validity,
            },
        )
        workbasket = object.transaction.workbasket

        if update_type != UpdateType.CREATE:
            # Make a new version of the contained model with the actual dates we
            # are testing, first finding the correct contained model to use.
            contained_obj = object
            if contained:
                with override_current_transaction(workbasket.current_transaction):
                    contained_obj = (
                        object.get_versions().current().follow_path(contained).get()
                    )
            contained_obj.new_version(
                workbasket,
                valid_between=contained_validity,
                update_type=update_type,
            )

        error_expected = update_type != UpdateType.DELETE and not fully_spanned
        with raises_if(business_rule.Violation, error_expected):
            business_rule(workbasket.current_transaction).validate(object)

    return check


@pytest.fixture
def date_ranges() -> Dates:
    return Dates()


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def policy_group(db) -> Group:
    group = factories.UserGroupFactory.create(name="Policy")

    for app_label, codename in [
        ("common", "add_trackedmodel"),
        ("common", "change_trackedmodel"),
        ("workbaskets", "add_workbasket"),
        ("workbaskets", "change_workbasket"),
    ]:
        group.permissions.add(
            Permission.objects.get(
                content_type__app_label=app_label,
                codename=codename,
            ),
        )
    return group


@pytest.fixture
def valid_user(db, policy_group):
    user = factories.UserFactory.create()
    policy_group.user_set.add(user)
    return user


@pytest.fixture
def valid_user_client(client, valid_user):
    client.force_login(valid_user)
    return client


@pytest.fixture
def superuser():
    user = factories.UserFactory.create(is_superuser=True, is_staff=True)
    return user


@pytest.fixture
def superuser_client(client, superuser):
    client.force_login(superuser)
    return client


@pytest.fixture
@given(parsers.parse("a valid user named {username}"), target_fixture="a_valid_user")
def a_valid_user(username):
    return factories.UserFactory.create(username=username)


@given(parsers.parse("I am logged in as {username}"), target_fixture="logged_in")
def logged_in(client, username):
    user = get_user_model().objects.get(username=username)
    client.force_login(user)


@given(
    parsers.parse("{username} is in the Policy group"),
    target_fixture="user_in_policy_group",
)
def user_in_policy_group(client, policy_group, username):
    user = get_user_model().objects.get(username=username)
    policy_group.user_set.add(user)


@pytest.fixture
def valid_user_api_client(api_client, valid_user) -> APIClient:
    api_client.force_login(valid_user)
    return api_client


@pytest.fixture
def taric_schema(settings) -> etree.XMLSchema:
    with open(settings.PATH_XSD_TARIC) as xsd_file:
        return etree.XMLSchema(etree.parse(xsd_file))


@pytest.fixture
def new_workbasket() -> WorkBasket:
    workbasket = factories.WorkBasketFactory.create(
        status=WorkflowStatus.EDITING,
    )
    with factories.TransactionFactory.create(workbasket=workbasket):
        factories.FootnoteTypeFactory.create_batch(2)

    return workbasket


@pytest.fixture
def approved_workbasket():
    return factories.ApprovedWorkBasketFactory.create()


@pytest.fixture
@given("there is a current workbasket")
def session_workbasket(client, new_workbasket):
    new_workbasket.save_to_session(client.session)
    client.session.save()
    return new_workbasket


@pytest.fixture(scope="function")
def seed_file_transaction():
    return factories.SeedFileTransactionFactory.create()


@pytest.fixture(scope="function")
def approved_transaction():
    return factories.ApprovedTransactionFactory.create()


@pytest.fixture(scope="function")
def unapproved_transaction():
    return factories.UnapprovedTransactionFactory.create()


@pytest.fixture(scope="function")
def workbasket():
    return factories.WorkBasketFactory.create()


@pytest.fixture(
    params=factories.TrackedModelMixin.__subclasses__(),
    ids=[
        factory._meta.model.__name__
        for factory in factories.TrackedModelMixin.__subclasses__()
    ],
)
def trackedmodel_factory(request):
    """Fixture that provides every TrackedModel class."""
    return request.param


@pytest.fixture(
    params=factories.ValidityFactoryMixin.__subclasses__(),
    ids=[
        factory._meta.model.__name__
        for factory in factories.ValidityFactoryMixin.__subclasses__()
    ],
)
def validity_factory(request):
    return request.param


@pytest.fixture(
    params=(
        factories.AdditionalCodeDescriptionFactory,
        factories.CertificateDescriptionFactory,
        factories.GeographicalAreaDescriptionFactory,
        factories.GoodsNomenclatureDescriptionFactory,
        factories.FootnoteDescriptionFactory,
        factories.TestModelDescription1Factory,
    ),
)
def description_factory(request):
    return request.param


@pytest.fixture
def use_create_form(valid_user_api_client: APIClient):
    """
    use_create_form, ported from use_update_form.

    use_create_form works with the model class, unlike use_update_from which
    works from an instance of a model class.

    Because this function creates data there is no initial instance to inspect
    so the implementation cannot use helpers that rely on a model instance like
    get_identifying_fields to build its data.

    Where practical this raises the same or equivalent assertions as
    use_update_form
    """

    def use(Model: Type[TrackedModel], new_data: Callable[Dict[str, str]]):
        """
        :param Model: Model class to test
        :param new_data function to populate form initial data.
        """
        prefix = Model.get_url_pattern_name_prefix()
        # Prefix will be along the lines of additional_code
        create_url = reverse(f"{prefix}-ui-create")
        assert create_url, f"No create page found for {Model}"

        # Initial rendering of url
        response = valid_user_api_client.get(create_url)
        assert response.status_code == 200

        initial_form = response.context_data["form"]
        data = get_form_data(initial_form)

        # Submit the edited data and if we expect success ensure we are redirected
        realised_data = new_data(data)
        data.update(realised_data)

        # There is no model instance to fetch identifying_fields from, construct
        # them from the provided form data.
        identifying_values = {
            k: data.get(k) for k in Model.identifying_fields if "__" not in k
        }

        response = valid_user_api_client.post(create_url, data)

        # Check that if we expect failure that the new data was not persisted
        if response.status_code not in (301, 302):
            assert not Model.objects.filter(**identifying_values).exists()
            raise ValidationError(
                f"Create form contained errors: {dict(response.context_data['form'].errors)}",
            )

        new_version = Model.objects.filter(**identifying_values).get()

        # Check that the new version is an update and is not approved yet
        assert new_version.update_type == UpdateType.CREATE
        assert not new_version.transaction.workbasket.approved

        return new_version

    return use


@pytest.fixture
def use_edit_view(valid_user_api_client: APIClient):
    def use(obj: TrackedModel, data_changes: dict[str, str]):
        Model = type(obj)
        obj_count = Model.objects.filter(**obj.get_identifying_fields()).count()
        url = obj.get_url("edit")

        # Check initial form rendering.
        get_response = valid_user_api_client.get(url)
        assert get_response.status_code == 200

        # Edit and submit the data.
        initial_form = get_response.context_data["form"]
        form_data = get_form_data(initial_form)
        form_data.update(data_changes)
        post_response = valid_user_api_client.post(url, form_data)

        # POSTing a real edits form should never create new object instances.
        assert Model.objects.filter(**obj.get_identifying_fields()).count() == obj_count
        if post_response.status_code not in (301, 302):
            raise ValidationError(
                f"Form contained errors: {dict(post_response.context_data['form'].errors)}",
            )

    return use


@pytest.fixture
def use_update_form(valid_user_api_client: APIClient):
    """
    Uses the default create form and view for a model with update_type=UPDATE.

    The ``object`` param is the TrackedModel instance for which a new UPDATE
    instance is to be created.
    The ``new_data`` dictionary should contain callable objects that when passed
    the existing value will return a new value to be sent with the form.

    Will raise :class:`~django.core.exceptions.ValidationError` if form thinks
    that the passed data contains errors.
    """

    def use(object: TrackedModel, new_data: Callable[[TrackedModel], dict[str, Any]]):
        model = type(object)
        versions = set(
            model.objects.filter(**object.get_identifying_fields()).values_list(
                "pk",
                flat=True,
            ),
        )

        # Visit the edit page and ensure it is a success
        edit_url = object.get_url("edit")
        assert edit_url, f"No edit page found for {object}"
        response = valid_user_api_client.get(edit_url)
        assert response.status_code == 200

        # Get the data out of the edit page
        # and override it with any data that has been passed in
        data = get_form_data(response.context_data["form"])

        # Submit the edited data and if we expect success ensure we are redirected
        realised_data = new_data(object)
        assert set(realised_data.keys()).issubset(data.keys())
        data.update(realised_data)
        response = valid_user_api_client.post(edit_url, data)

        # Check that if we expect failure that the new data was not persisted
        if response.status_code not in (301, 302):
            assert (
                set(
                    model.objects.filter(**object.get_identifying_fields()).values_list(
                        "pk",
                        flat=True,
                    ),
                )
                == versions
            )
            raise ValidationError(
                f"Update form contained errors: {response.context_data['form'].errors}",
            )

        # Check that what we asked to be changed has been persisted
        response = valid_user_api_client.get(edit_url)
        assert response.status_code == 200
        data = get_form_data(response.context_data["form"])
        for key in realised_data:
            assert data[key] == realised_data[key]

        # Check that if success was expected that the new version was persisted
        new_version = model.objects.exclude(pk=object.pk).get(
            version_group=object.version_group,
        )
        assert new_version != object

        # Check that the new version is an update and is not approved yet
        assert new_version.update_type == UpdateType.UPDATE
        assert new_version.transaction != object.transaction
        assert not new_version.transaction.workbasket.approved
        return new_version

    return use


@pytest.fixture
def use_delete_form(valid_user_api_client: APIClient):
    """
    Uses the default delete form and view for a model to delete an object, and
    returns the deleted version of the object.

    Will raise :class:`~django.core.exceptions.ValidationError` if form thinks
    that the object cannot be deleted..
    """

    def use(object: TrackedModel):
        model = type(object)
        versions = set(
            model.objects.filter(**object.get_identifying_fields()).values_list(
                "pk",
                flat=True,
            ),
        )

        # Visit the delete page and ensure it is a success
        delete_url = object.get_url("delete")
        assert delete_url, f"No delete page found for {object}"
        response = valid_user_api_client.get(delete_url)
        assert response.status_code == 200

        # Get the data out of the delete page
        data = get_form_data(response.context_data["form"])
        response = valid_user_api_client.post(delete_url, data)

        # Check that if we expect failure that the new data was not persisted
        if response.status_code not in (301, 302):
            assert (
                set(
                    model.objects.filter(**object.get_identifying_fields()).values_list(
                        "pk",
                        flat=True,
                    ),
                )
                == versions
            )
            raise ValidationError(
                f"Delete form contained errors: {response.context_data['form'].errors}",
            )

        # Check that the delete persisted and we can't delete again
        response = valid_user_api_client.get(delete_url)
        assert response.status_code == 404

        # Check that if success was expected that the new version was persisted
        new_version = model.objects.exclude(pk=object.pk).get(
            version_group=object.version_group,
        )
        assert new_version != object

        # Check that the new version is a delete and is not approved yet
        assert new_version.update_type == UpdateType.DELETE
        assert new_version.transaction != object.transaction
        assert not new_version.transaction.workbasket.approved
        return new_version

    return use


@pytest.fixture
def import_xml(valid_user):
    def run_import(xml, workflow_status=WorkflowStatus.PUBLISHED, record_group=None):
        process_taric_xml_stream(
            xml,
            workbasket_id=None,
            workbasket_status=workflow_status,
            partition_scheme=get_partition_scheme(),
            username=valid_user.username,
            record_group=record_group,
        )

    return run_import


@pytest.fixture
def export_xml(valid_user_api_client):
    return partial(export_workbasket, valid_user_api_client=valid_user_api_client)


@pytest.fixture
def run_xml_import(import_xml, settings):
    """
    Returns a function for checking a model can be imported correctly.

    The function takes the following parameters:
        model: A model instance, or a factory class used to build the model.
            This model should not already exist in the database.
        serializer: An optional serializer class to convert the model to its TARIC XML
            representation. If not provided, the function attempts to use a serializer
            class named after the model, eg measures.serializers.<model-class-name>Serializer
        record_group: A taric record group, which can be used to trigger
            specific importer behaviour, e.g. for handling commodity code changes

    The function serializes the model to TARIC XML, inputs this to the importer, then
    fetches the newly created model from the database and compares the fields.

    It returns the imported object if there are no discrepancies, allowing it to be
    further tested.
    """

    def check(
        factory: Callable[[], TrackedModel],
        serializer: Type[TrackedModelSerializer],
        record_group: Sequence[str] = None,
        workflow_status: WorkflowStatus = WorkflowStatus.PUBLISHED,
    ) -> TrackedModel:
        get_nursery().cache.clear()
        settings.SKIP_WORKBASKET_VALIDATION = True

        model = factory()
        model_class = type(model)
        assert isinstance(
            model,
            TrackedModel,
        ), "A factory that returns an object instance needs to be provided"

        xml = generate_test_import_xml(
            [serializer(model, context={"format": "xml"}).data],
        )

        import_xml(xml, workflow_status, record_group)

        db_kwargs = model.get_identifying_fields()
        workbasket = WorkBasket.objects.last()
        assert workbasket is not None

        try:
            imported = model_class.objects.approved_up_to_transaction(
                workbasket.current_transaction,
            ).get(**db_kwargs)
        except model_class.DoesNotExist:
            if model.update_type == UpdateType.DELETE:
                imported = (
                    model_class.objects.versions_up_to(workbasket.current_transaction)
                    .filter(**db_kwargs)
                    .last()
                )
            else:
                raise

        assert_records_match(model, imported)
        return imported

    return check


@pytest.fixture(
    params=[v for v in UpdateType],
    ids=[v.name for v in UpdateType],
)
def update_type(request):
    return request.param


@pytest.fixture
def imported_fields_match(run_xml_import, update_type):
    """
    Returns a function that serializes a model to TARIC XML, inputs this to the
    importer, then fetches the newly created model from the database and
    compares the fields. This is much the same functionality as `run_xml_import`
    but with some adjustments for updates and deletes.

    A dict of dependencies can also be injected which will be added to the model
    when it is built. For any of the values that are factories, they will be
    built into real models and saved before the import is carried out.

    In addition to `run_xml_import` a previous version of the object is
    generated when testing updates or deletes as these can only occur after a
    create. The data around version groups is also tested.
    """

    def check(
        factory: Type[DjangoModelFactory],
        serializer: Type[TrackedModelSerializer],
        dependencies: Optional[Dict[str, Any]] = None,
    ):
        Model: Type[TrackedModel] = factory._meta.model
        previous_version: TrackedModel = None

        # Build kwargs and dependencies needed to make a complete model. This
        # can't rely on the factory itself as the dependencies need to be in the
        # database before the import else they will also appear in the XML.
        kwargs = {}
        for name, dependency_model in (dependencies or {}).items():
            if isinstance(dependency_model, type) and issubclass(
                dependency_model,
                DjangoModelFactory,
            ):
                kwargs[name] = dependency_model.create()
            else:
                kwargs[name] = dependency_model

        if update_type in (UpdateType.UPDATE, UpdateType.DELETE):
            previous_version = factory.create(**kwargs)
            kwargs.update(previous_version.get_identifying_fields())

        updated_model = run_xml_import(
            lambda: factory.build(
                update_type=update_type,
                **kwargs,
            ),
            serializer,
        )

        version_group = (previous_version or updated_model).version_group
        version_group.refresh_from_db()
        assert version_group.versions.count() == (
            1 if update_type == UpdateType.CREATE else 2
        )
        assert version_group == updated_model.version_group
        assert version_group.current_version == updated_model
        assert version_group.current_version.update_type == update_type
        return updated_model

    return check


@pytest.fixture
def s3():
    with mock_s3() as moto:
        moto.start()
        s3 = boto3.client("s3")
        yield s3


@pytest.fixture
def s3_resource():
    with mock_s3() as moto:
        moto.start()
        s3 = boto3.resource("s3")
        yield s3


@pytest.fixture
def s3_bucket_names(s3):
    def run():
        return [bucket_info["Name"] for bucket_info in s3.list_buckets()["Buckets"]]

    return run


@pytest.fixture
def s3_object_names(s3):
    def run(bucket_name):
        return [
            contents["Key"]
            for contents in s3.list_objects(Bucket=bucket_name)["Contents"]
        ]

    return run


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


def make_storage_mock(s3, storage_class, **override_settings):
    storage = storage_class(**override_settings)
    storage._connections.connection = type(storage.connection)(client=s3)
    s3.create_bucket(
        Bucket=storage.bucket_name,
        CreateBucketConfiguration={
            "LocationConstraint": settings.AWS_S3_REGION_NAME,
        },
    )

    return storage


@pytest.fixture
def hmrc_storage(s3):
    """Patch HMRCStorage with moto so that nothing is really uploaded to s3."""
    from exporter.storages import HMRCStorage

    return make_storage_mock(
        s3,
        HMRCStorage,
        bucket_name=settings.HMRC_STORAGE_BUCKET_NAME,
    )


@pytest.fixture
def sqlite_storage(s3, s3_bucket_names):
    """Patch SQLiteStorage with moto so that nothing is really uploaded to
    s3."""
    from exporter.storages import SQLiteStorage

    storage = make_storage_mock(
        s3,
        SQLiteStorage,
        bucket_name=settings.SQLITE_STORAGE_BUCKET_NAME,
    )
    assert storage.endpoint_url is settings.SQLITE_S3_ENDPOINT_URL
    assert storage.access_key is settings.SQLITE_S3_ACCESS_KEY_ID
    assert storage.secret_key is settings.SQLITE_S3_SECRET_ACCESS_KEY
    assert storage.bucket_name in s3_bucket_names()
    return storage


@pytest.fixture(
    params=(
        (make_duplicate_record, True),
        (make_non_duplicate_record, False),
    ),
    ids=(
        "duplicate",
        "not_duplicate",
    ),
)
def assert_handles_duplicates(request):
    def do_assert(
        factory: Type[factories.TrackedModelMixin],
        business_rule: Type[BusinessRule],
        identifying_fields: Optional[Dict[str, Any]] = None,
    ):
        make_record, error_expected = request.param
        duplicate = make_record(factory, identifying_fields)
        with raises_if(BusinessRuleViolation, error_expected):
            business_rule(duplicate.transaction).validate(duplicate)

    return do_assert


@pytest.fixture
def delete_record():
    """Provides a function for deleting a record."""

    def delete(model):
        return model.new_version(
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


@pytest.fixture
def in_use_check_respects_deletes(valid_user):
    """Provides a test function for creating a pair of records with a dependency
    and checking that the "in_use" method of the dependee returns False when all
    dependant records are unapproved or deleted."""

    def check(
        factory,
        in_use_check,
        dependant_factory,
        relation,
        through=None,
        **extra_kwargs,
    ):
        instance = factory.create()
        in_use = getattr(instance, in_use_check)
        assert not in_use(instance.transaction), f"New {instance!r} already in use"

        workbasket = factories.WorkBasketFactory.create(
            status=WorkflowStatus.PROPOSED,
        )
        with workbasket.new_transaction():
            create_kwargs = {relation: instance}
            if through:
                create_kwargs = {relation: getattr(instance, through)}
            dependant = dependant_factory.create(**create_kwargs, **extra_kwargs)
        assert in_use(
            dependant.transaction,
        ), f"Unapproved {instance!r} not in use in draft workbasket"
        assert not in_use(
            Transaction.approved.last(),
        ), f"Unapproved {instance!r} already in use"

        with patch(
            "exporter.tasks.upload_workbaskets.delay",
        ):
            workbasket.approve(
                valid_user.pk,
                settings.TRANSACTION_SCHEMA,
            )
        workbasket.save()
        assert in_use(dependant.transaction), f"Approved {instance!r} not in use"

        deleted = dependant.new_version(
            workbasket,
            update_type=UpdateType.DELETE,
        )
        assert not in_use(deleted.transaction), f"Deleted {instance!r} in use"

        return True

    return check


@pytest.fixture(
    params=[
        (UpdateType.DELETE, True),
        (UpdateType.UPDATE, True),
        (UpdateType.CREATE, False),
    ],
)
def check_first_update_validation(request):
    """
    Provides a test function for creating records and checking the application
    of update type validity business rule:

    - The first update must be of type Create.
    """
    update_type, expected_error = request.param

    def check(factory):
        instance = factory.create(update_type=update_type)

        # Create a future instance – the business rule should ignore this
        # but the test for CREATE will fail if it does not.
        factory.create(
            update_type=UpdateType.UPDATE,
            transaction__workbasket=instance.transaction.workbasket,
            transaction__order=instance.transaction.order + 1,
        )

        with raises_if(UpdateValidity.Violation, expected_error):
            UpdateValidity(instance.transaction).validate(instance)

        return True

    return check


@pytest.fixture(
    params=[
        (UpdateType.CREATE, True),
        (UpdateType.UPDATE, False),
        (UpdateType.DELETE, False),
    ],
)
def check_later_update_validation(request):
    """
    Provides a test function for creating records and checking the application
    of update type validity business rule:

    - Subsequent updates must not be of type Create.
    """
    update_type, expected_error = request.param

    def check(factory):
        first_instance = factory.create()
        instance = factory.create(
            update_type=update_type,
            version_group=first_instance.version_group,
        )

        with raises_if(UpdateValidity.Violation, expected_error):
            UpdateValidity(instance.transaction).validate(instance)

        return True

    return check


@pytest.fixture
def check_after_delete_update_validation():
    """
    Provides a test function for creating records and checking the application
    of update type validity business rule:

    - After an update of type Delete, there must be no further updates.
    """

    def check(factory):
        transaction = factories.TransactionFactory.create()
        first_instance = factory.create(update_type=UpdateType.DELETE)
        second_instance = factory.create(
            transaction=transaction,
            update_type=UpdateType.UPDATE,
            version_group=first_instance.version_group,
        )

        with pytest.raises(
            UpdateValidity.Violation,
        ):
            UpdateValidity(second_instance.transaction).validate(
                second_instance,
            )

        return True

    return check


@pytest.fixture
def check_only_one_version_updated_in_transaction():
    """
    Provides a test function for creating records and checking the application
    of update type validity business rule:

    - Only one version may be updated in a single transaction.
    """

    def check(factory):
        transaction = factories.TransactionFactory.create()
        first_instance = factory.create(
            transaction=transaction,
            update_type=UpdateType.UPDATE,
        )
        second_instance = factory.create(
            transaction=transaction,
            update_type=UpdateType.UPDATE,
            version_group=first_instance.version_group,
        )

        with pytest.raises(
            UpdateValidity.Violation,
        ):
            UpdateValidity(second_instance.transaction).validate(second_instance)

        return True

    return check


@pytest.fixture
def check_update_validation(
    check_first_update_validation,
    check_later_update_validation,
    check_after_delete_update_validation,
    check_only_one_version_updated_in_transaction,
):
    """Provides a test function for creating records and checking the
    application of update type validity business rules."""

    def check(factory):
        assert check_first_update_validation(
            factory,
        )
        assert check_later_update_validation(
            factory,
        )
        assert check_after_delete_update_validation(
            factory,
        )
        assert check_only_one_version_updated_in_transaction(
            factory,
        )
        assert UpdateValidity in factory._meta.model.business_rules
        return True

    return check


@pytest.fixture
def response():
    """Hacky fixture to enable passing the client response between BDD steps."""
    return {}


@then(parsers.parse('I see the form error message "{error_message}"'))
def form_error_shown(response, error_message):
    response_html = parse_html(response["response"].content.decode())
    assert error_message in response_html


@pytest.fixture
def staff_user():
    user = factories.UserFactory.create(is_staff=True)
    return user


@dataclass
class UnorderedTransactionData:
    existing_transaction: Transaction
    new_transaction: Transaction


@pytest.fixture(scope="function")
def unordered_transactions():
    """
    Fixture that creates some transactions, where one is a draft.

    The draft transaction has approved transactions on either side, this allows
    testing of save_draft and it's callers to verify the transactions are getting
    sorted.

    UnorderedTransactionData is returned, so the user can set the new_transaction partition to DRAFT
    and while also using an existing_transaction.
    """
    from common.tests.factories import ApprovedTransactionFactory
    from common.tests.factories import FootnoteFactory
    from common.tests.factories import UnapprovedTransactionFactory

    FootnoteFactory.create(transaction=ApprovedTransactionFactory.create())

    new_transaction = UnapprovedTransactionFactory.create(order=100)
    FootnoteFactory.create(transaction=ApprovedTransactionFactory.create())

    existing_transaction = Transaction.objects.filter(
        partition=TransactionPartition.REVISION,
    ).last()

    assert new_transaction.partition == TransactionPartition.DRAFT
    assert existing_transaction.order > 1

    return UnorderedTransactionData(existing_transaction, new_transaction)


@pytest.fixture
def session_request(client):
    session = client.session
    session.save()
    request = RequestFactory()
    request.session = session

    return request


@pytest.fixture
def session_with_workbasket(session_request, workbasket):
    session_request.session.update({"workbasket": {"id": workbasket.pk}})
    return session_request


@pytest.fixture
def model1_with_history(date_ranges):
    return model_with_history(
        factories.TestModel1Factory,
        date_ranges,
        version_group=factories.VersionGroupFactory.create(),
        sid=1,
    )


@pytest.fixture
def model2_with_history(date_ranges):
    return model_with_history(
        factories.TestModel2Factory,
        date_ranges,
        version_group=factories.VersionGroupFactory.create(),
        custom_sid=1,
    )


# As per this open issue with pytest https://github.com/pytest-dev/pytest/issues/5997,
# some tests can only be run with global capturing disabled. Until we find a way
# to disable capturing from within the test itself we can mark tests that should be skipped
# unless global capturing is disabled via the "-s" flag.

# TODO https://uktrade.atlassian.net/browse/TP2000-591

# See pytest docs for implementation below
# https://docs.pytest.org/en/7.1.x/example/simple.html#control-skipping-of-tests-according-to-command-line-option


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "s: mark test as needing global capturing disabled to run",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("-s") == "no":
        # -s given in cli: do not skip s tests
        return
    skip_s = pytest.mark.skip(reason="need -s option to run")
    for item in items:
        if "s" in item.keywords:
            item.add_marker(skip_s)
