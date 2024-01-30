from __future__ import annotations

import contextlib
from dataclasses import dataclass
from functools import partial
from typing import Any
from typing import Callable
from typing import Dict
from typing import Optional
from typing import Sequence
from typing import Tuple
from typing import Type
from unittest.mock import MagicMock
from unittest.mock import patch

import boto3
import factory
import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.management import create_contenttypes
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import DEFAULT_DB_ALIAS
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

from checks.tests.factories import TransactionCheckFactory
from common.business_rules import BusinessRule
from common.business_rules import BusinessRuleViolation
from common.business_rules import UpdateValidity
from common.business_rules import ValidityPeriodContained
from common.models import TrackedModel
from common.models.transactions import Transaction
from common.models.transactions import TransactionPartition
from common.models.utils import override_current_transaction
from common.serializers import TrackedModelSerializer
from common.tariffs_api import Endpoints
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
from common.validators import ApplicabilityCode
from common.validators import UpdateType
from importer.models import ImportBatchStatus
from importer.nursery import get_nursery
from importer.taric import process_taric_xml_stream
from measures.models import DutyExpression
from measures.models import MeasureConditionComponent
from measures.models import Measurement
from measures.models import MeasurementUnit
from measures.models import MeasurementUnitQualifier
from measures.models import MonetaryUnit
from measures.parsers import DutySentenceParser
from publishing.models import PackagedWorkBasket
from tasks.models import UserAssignment
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
def tap_migrator_factory(migrator_factory):
    """
    This fixture is an override of the django-test-migrations fixture of
    `django_test_migrations.contrib.pytest_plugin.migrator_factory()`.

    One or two issues in Django, and / or related libraries that TAP uses for
    its migration unit testing, continues to cause problems in migration unit
    tests. A couple of examples of the reported issue:
    https://code.djangoproject.com/ticket/10827
    /PS-IGNORE---https://github.com/wemake-services/django-test-migrations/blob/93db540c00a830767eeab5f90e2eef1747c940d4/django_test_migrations/migrator.py#L73


    An initial migration must reference ContentType instances (in the DB).
    This can occur when inserting Permission objects during
    `migrator.apply_initial_migration()` execution.

    At that point, a stale ContentType cache can give an incorrect account of
    ContentType DB table state, so attempts by an initial migration to insert
    those Permission objects fails on foreign key violations because they're
    referencing missing ContentType objects (they're not in the database, only
    in the ContentType cache).
    """
    ContentType.objects.clear_cache()
    return migrator_factory


@pytest.fixture
def migrator(tap_migrator_factory):
    """Override of `django_test_migrations.contrib.pytest_plugin.migrator()`,
    substituting a call to
    `django_test_migrations.contrib.pytest_plugin.migrator_factory()` with a
    locally overriden instance, `tap_migrator_factory()`."""
    return tap_migrator_factory(DEFAULT_DB_ALIAS)


@pytest.fixture
def setup_content_types():
    """This fixture is used to set-up content types, needed for migration
    testing, when a clean new database and the content types have not been
    populated yet."""

    def _method(apps):
        tamato_apps = settings.DOMAIN_APPS + settings.TAMATO_APPS

        app_labels = []

        for app in apps.get_app_configs():
            app_labels.append(app.label)

        for app_name in tamato_apps:
            app_label = app_name.split(".")[0]
            if app_label in app_labels:
                app_config = apps.get_app_config(app_label)
                app_config.models_module = True

                create_contenttypes(app_config)

    return _method


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
        ("workbaskets", "view_workbasket"),
        ("publishing", "consume_from_packaging_queue"),
        ("publishing", "manage_packaging_queue"),
        ("publishing", "view_envelope"),
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
def client_with_current_workbasket(client, valid_user):
    client.force_login(valid_user)
    workbasket = factories.WorkBasketFactory.create(
        status=WorkflowStatus.EDITING,
    )
    workbasket.assign_to_user(valid_user)
    return client


@pytest.fixture
def client_with_current_workbasket_no_permissions(client):
    """Returns a client with a logged in user who has a current workbasket but
    no permissions."""
    user = factories.UserFactory.create()
    client.force_login(user)
    workbasket = factories.WorkBasketFactory.create(
        status=WorkflowStatus.EDITING,
    )
    workbasket.assign_to_user(user)
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
def api_client_with_current_workbasket(api_client, valid_user) -> APIClient:
    api_client.force_login(valid_user)
    workbasket = factories.WorkBasketFactory.create(
        status=WorkflowStatus.EDITING,
    )
    workbasket.assign_to_user(valid_user)
    return api_client


@pytest.fixture
def taric_schema(settings) -> etree.XMLSchema:
    with open(settings.PATH_XSD_TARIC) as xsd_file:
        return etree.XMLSchema(etree.parse(xsd_file))


@pytest.fixture
def new_workbasket() -> WorkBasket:
    workbasket = factories.AssignedWorkBasketFactory.create()
    with factories.TransactionFactory.create(workbasket=workbasket):
        factories.FootnoteTypeFactory.create_batch(2)

    return workbasket


@pytest.fixture
def queued_workbasket():
    return factories.QueuedWorkBasketFactory.create()


@pytest.fixture
def published_additional_code_type(queued_workbasket):
    return factories.AdditionalCodeTypeFactory(
        transaction=queued_workbasket.new_transaction(),
    )


@pytest.fixture
def published_certificate_type(queued_workbasket):
    return factories.CertificateTypeFactory(
        transaction=queued_workbasket.new_transaction(),
    )


@pytest.fixture
def published_footnote_type(queued_workbasket):
    return factories.FootnoteTypeFactory(
        transaction=queued_workbasket.new_transaction(),
    )


@pytest.fixture
@given("there is a current workbasket")
def user_workbasket(client, valid_user, new_workbasket) -> WorkBasket:
    """Returns a workbasket which has been assigned to a valid logged-in
    user."""
    client.force_login(valid_user)
    new_workbasket.assign_to_user(valid_user)
    return new_workbasket


@pytest.fixture
def user_empty_workbasket(client, valid_user) -> WorkBasket:
    client.force_login(valid_user)
    workbasket = factories.WorkBasketFactory.create(
        status=WorkflowStatus.EDITING,
    )
    workbasket.assign_to_user(valid_user)
    return workbasket


@pytest.fixture
def queued_workbasket_factory():
    def factory_method():
        workbasket = factories.WorkBasketFactory.create(
            status=WorkflowStatus.QUEUED,
        )
        with factories.ApprovedTransactionFactory.create(workbasket=workbasket):
            factories.FootnoteTypeFactory()
            factories.AdditionalCodeFactory()
        return workbasket

    return factory_method


@pytest.fixture
def published_workbasket_factory():
    def factory_method():
        workbasket = factories.PublishedWorkBasketFactory()
        with factories.ApprovedTransactionFactory.create(workbasket=workbasket):
            factories.FootnoteTypeFactory()
            factories.AdditionalCodeFactory()
        return workbasket

    return factory_method


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
def unapproved_checked_transaction(unapproved_transaction):
    TransactionCheckFactory.create(
        transaction=unapproved_transaction,
        completed=True,
        successful=True,
    )

    return unapproved_transaction


@pytest.fixture(scope="function")
def workbasket():
    """
    Returns existing workbasket if one already exists otherwise creates a new
    one.

    This is as some tests already have a workbasket when this is called.
    """
    if WorkBasket.objects.all().count() > 0:
        workbasket = WorkBasket.objects.first()
    else:
        workbasket = factories.WorkBasketFactory.create()

    task = factories.TaskFactory.create(workbasket=workbasket)
    factories.UserAssignmentFactory.create(
        assignment_type=UserAssignment.AssignmentType.WORKBASKET_WORKER,
        task=task,
    )
    factories.UserAssignmentFactory.create(
        assignment_type=UserAssignment.AssignmentType.WORKBASKET_REVIEWER,
        task=task,
    )
    return workbasket


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
def use_create_form(api_client_with_current_workbasket):
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

    def use(
        Model: Type[TrackedModel],
        new_data: Callable[[Dict[str, str]], Dict[str, str]],
    ):
        """
        :param Model: Model class to test
        :param new_data function to populate form initial data.
        """
        prefix = Model.get_url_pattern_name_prefix()
        # Prefix will be along the lines of additional_code
        create_url = reverse(f"{prefix}-ui-create")
        assert create_url, f"No create page found for {Model}"

        # Initial rendering of url
        response = api_client_with_current_workbasket.get(create_url)
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

        response = api_client_with_current_workbasket.post(create_url, data)

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
def use_edit_view(api_client_with_current_workbasket):
    """
    Uses the default edit form and view for a model in a workbasket with EDITING
    status.

    The ``object`` param is the TrackedModel instance that is to be edited and
    saved, which should not create a new version.
    ``data_changes`` should be a dictionary to apply to the object, effectively
    applying edits.

    Will raise :class:`~django.core.exceptions.ValidationError` if the form
    contains errors.
    """

    def use(obj: TrackedModel, data_changes: dict[str, str]):
        Model = type(obj)
        obj_count = Model.objects.filter(**obj.get_identifying_fields()).count()
        url = obj.get_url("edit")

        # Check initial form rendering.
        get_response = api_client_with_current_workbasket.get(url)
        assert get_response.status_code == 200

        # Edit and submit the data.
        initial_form = get_response.context_data["form"]
        form_data = get_form_data(initial_form)
        form_data.update(data_changes)
        post_response = api_client_with_current_workbasket.post(url, form_data)

        # POSTing a real edits form should never create new object instances.
        assert Model.objects.filter(**obj.get_identifying_fields()).count() == obj_count
        if post_response.status_code not in (301, 302):
            raise ValidationError(
                f"Form contained errors: {dict(post_response.context_data['form'].errors)}",
            )

    return use


@pytest.fixture
def use_update_form(api_client_with_current_workbasket):
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
        response = api_client_with_current_workbasket.get(edit_url)
        assert response.status_code == 200

        # Get the data out of the edit page
        # and override it with any data that has been passed in
        data = get_form_data(response.context_data["form"])

        # Submit the edited data and if we expect success ensure we are redirected
        realised_data = new_data(object)
        assert set(realised_data.keys()).issubset(data.keys())
        data.update(realised_data)
        response = api_client_with_current_workbasket.post(edit_url, data)

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
        response = api_client_with_current_workbasket.get(edit_url)
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
def use_delete_form(api_client_with_current_workbasket):
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
        response = api_client_with_current_workbasket.get(delete_url)
        assert response.status_code == 200

        # Get the data out of the delete page
        data = get_form_data(response.context_data["form"])
        response = api_client_with_current_workbasket.post(delete_url, data)

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
        response = api_client_with_current_workbasket.get(delete_url)
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
    try:
        s3.create_bucket(
            Bucket=storage.bucket_name,
            CreateBucketConfiguration={
                "LocationConstraint": settings.AWS_S3_REGION_NAME,
            },
        )
    except s3.exceptions.BucketAlreadyExists:
        return storage

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


@pytest.fixture
def envelope_storage(s3, s3_bucket_names):
    """Patch EnvelopeStorage with moto so that nothing is really uploaded to
    s3."""
    from publishing.storages import EnvelopeStorage

    storage = make_storage_mock(
        s3,
        EnvelopeStorage,
        bucket_name=settings.HMRC_PACKAGING_STORAGE_BUCKET_NAME,
    )
    assert storage.endpoint_url is settings.S3_ENDPOINT_URL
    assert storage.access_key is settings.HMRC_PACKAGING_S3_ACCESS_KEY_ID
    assert storage.secret_key is settings.HMRC_PACKAGING_S3_SECRET_ACCESS_KEY
    assert storage.bucket_name in s3_bucket_names()
    return storage


@pytest.fixture
def loading_report_storage(s3):
    """Patch LoadingReportStorage with moto so that nothing is really uploaded
    to s3."""
    from publishing.storages import LoadingReportStorage

    return make_storage_mock(
        s3,
        LoadingReportStorage,
        bucket_name=settings.HMRC_PACKAGING_STORAGE_BUCKET_NAME,
    )


@pytest.fixture
def importer_storage(s3):
    """Patch CommodityImporterStorage with moto so that nothing is really
    uploaded to s3."""
    from importer.storages import CommodityImporterStorage

    storage = make_storage_mock(
        s3,
        CommodityImporterStorage,
        bucket_name=settings.IMPORTER_STORAGE_BUCKET_NAME,
    )
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
        factory_instance,
        reference_field_name: str,
        teardown: Optional[Callable[[Any], Any]] = None,
    ):
        # relies on private API
        dependency_declaration = factory_instance._meta.declarations[
            reference_field_name
        ]

        # if factory returns multiple options (factory.declarations.Maybe) we need to select the "no" option
        # (default factory) until we get to a factory we can then call get_factory() on. It does not really
        # matter since the factory will create and then delete the record, leaving a reference to the PK that was
        # removed.
        while isinstance(dependency_declaration, factory.declarations.Maybe):
            dependency_declaration = dependency_declaration.no

        dependency_factory = dependency_declaration.get_factory()

        dependency = dependency_factory.create()
        non_existent_id = dependency.pk

        if teardown:
            teardown(dependency)
        else:
            dependency.delete()

        record = factory_instance.create(
            **{f"{reference_field_name}_id": non_existent_id},
        )

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

        workbasket = factories.AssignedWorkBasketFactory.create()
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

        for tx in workbasket.transactions.all():
            TransactionCheckFactory.create(
                transaction=tx,
                successful=True,
                completed=True,
            )

        with patch(
            "exporter.tasks.upload_workbaskets.delay",
        ):
            workbasket.queue(
                valid_user.pk,
                settings.TRANSACTION_SCHEMA,
            )
        workbasket.save()
        assert in_use(dependant.transaction), f"Queued {instance!r} not in use"

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
    testing of save_draft and it's callers to verify the transactions are
    getting sorted.

    UnorderedTransactionData is returned, so the user can set the
    new_transaction partition to DRAFT and while also using an
    existing_transaction.
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
def session_request(client, valid_user):
    session = client.session
    session.save()
    request = RequestFactory()
    request.session = session
    request.user = valid_user

    return request


@pytest.fixture
def session_request_with_workbasket(client, valid_user):
    """
    Returns a request object which has a valid user and session associated.

    The valid user has a current workbasket.
    """
    client.force_login(valid_user)
    workbasket = factories.WorkBasketFactory.create(
        status=WorkflowStatus.EDITING,
    )
    workbasket.assign_to_user(valid_user)

    session = client.session
    session.save()
    request = RequestFactory()
    request.session = session
    request.user = valid_user
    return request


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


@pytest.fixture()
def quota_order_number():
    return factories.QuotaOrderNumberFactory()


@pytest.fixture
def mock_quota_api_no_data(requests_mock):
    yield requests_mock.get(url=Endpoints.QUOTAS.value, json={})


@pytest.fixture
def quotas_json():
    return {
        "data": [
            {
                "id": "12345",
                "type": "definition",
                "attributes": {
                    "quota_definition_sid": "12345",
                    "quota_order_number_id": "12345",
                    "initial_volume": "78849000.0",
                    "validity_start_date": "2023-01-01T00:00:00.000Z",
                    "validity_end_date": "2023-03-31T23:59:59.000Z",
                    "status": "Open",
                    "description": None,
                    "balance": "76766532.891",
                    "measurement_unit": "Kilogram (kg)",
                    "monetary_unit": None,
                    "measurement_unit_qualifier": None,
                    "last_allocation_date": "2023-01-10T00:00:00Z",
                    "suspension_period_start_date": None,
                    "suspension_period_end_date": None,
                    "blocking_period_start_date": None,
                    "blocking_period_end_date": None,
                },
                "relationships": {
                    "incoming_quota_closed_and_transferred_event": {"data": None},
                    "order_number": {"data": {"id": "1234", "type": "order_number"}},
                    "measures": {
                        "data": [
                            {"id": "1234", "type": "measure"},
                        ],
                    },
                    "quota_balance_events": {},
                },
            },
        ],
        "meta": {"pagination": {"page": 1, "per_page": 5, "total_count": 1}},
    }


@pytest.fixture
def importing_goods_import_batch():
    editing_workbasket = factories.WorkBasketFactory.create()
    return factories.ImportBatchFactory.create(
        goods_import=True,
        status=ImportBatchStatus.IMPORTING,
        workbasket_id=editing_workbasket.id,
    )


@pytest.fixture
def failed_goods_import_batch():
    editing_workbasket = factories.WorkBasketFactory.create()
    return factories.ImportBatchFactory.create(
        goods_import=True,
        status=ImportBatchStatus.FAILED,
        workbasket_id=editing_workbasket.id,
    )


@pytest.fixture
def completed_goods_import_batch():
    editing_workbasket = factories.WorkBasketFactory.create()
    return factories.ImportBatchFactory.create(
        goods_import=True,
        status=ImportBatchStatus.SUCCEEDED,
        workbasket_id=editing_workbasket.id,
    )


@pytest.fixture
def published_goods_import_batch():
    published_workbasket = factories.PublishedWorkBasketFactory.create()
    return factories.ImportBatchFactory.create(
        goods_import=True,
        status=ImportBatchStatus.SUCCEEDED,
        workbasket_id=published_workbasket.id,
    )


@pytest.fixture
def empty_goods_import_batch():
    archived_workbasket = factories.ArchivedWorkBasketFactory.create()
    return factories.ImportBatchFactory.create(
        goods_import=True,
        status=ImportBatchStatus.SUCCEEDED,
        workbasket_id=archived_workbasket.id,
    )


@pytest.fixture
def duty_sentence_parser(
    duty_expressions: Dict[int, DutyExpression],
    monetary_units: Dict[str, MonetaryUnit],
    measurements: Dict[Tuple[str, Optional[str]], Measurement],
) -> DutySentenceParser:
    return DutySentenceParser(
        duty_expressions.values(),
        monetary_units.values(),
        measurements.values(),
    )


@pytest.fixture
def percent_or_amount() -> DutyExpression:
    return factories.DutyExpressionFactory(
        sid=1,
        prefix="",
        duty_amount_applicability_code=ApplicabilityCode.MANDATORY,
        measurement_unit_applicability_code=ApplicabilityCode.PERMITTED,
        monetary_unit_applicability_code=ApplicabilityCode.PERMITTED,
    )


@pytest.fixture
def plus_percent_or_amount() -> DutyExpression:
    return factories.DutyExpressionFactory(
        sid=4,
        prefix="+",
        duty_amount_applicability_code=ApplicabilityCode.MANDATORY,
        measurement_unit_applicability_code=ApplicabilityCode.PERMITTED,
        monetary_unit_applicability_code=ApplicabilityCode.PERMITTED,
    )


@pytest.fixture
def plus_agri_component() -> DutyExpression:
    return factories.DutyExpressionFactory(
        sid=12,
        prefix="+ AC",
        duty_amount_applicability_code=ApplicabilityCode.NOT_PERMITTED,
        measurement_unit_applicability_code=ApplicabilityCode.PERMITTED,
        monetary_unit_applicability_code=ApplicabilityCode.PERMITTED,
    )


@pytest.fixture
def plus_amount_only() -> DutyExpression:
    return factories.DutyExpressionFactory(
        sid=20,
        prefix="+",
        duty_amount_applicability_code=ApplicabilityCode.MANDATORY,
        measurement_unit_applicability_code=ApplicabilityCode.MANDATORY,
        monetary_unit_applicability_code=ApplicabilityCode.MANDATORY,
    )


@pytest.fixture
def nothing() -> DutyExpression:
    return factories.DutyExpressionFactory(
        sid=37,
        prefix="NIHIL",
        duty_amount_applicability_code=ApplicabilityCode.NOT_PERMITTED,
        measurement_unit_applicability_code=ApplicabilityCode.NOT_PERMITTED,
        monetary_unit_applicability_code=ApplicabilityCode.NOT_PERMITTED,
    )


@pytest.fixture
def supplementary_unit() -> DutyExpression:
    return factories.DutyExpressionFactory(
        sid=99,
        prefix="",
        duty_amount_applicability_code=ApplicabilityCode.PERMITTED,
        measurement_unit_applicability_code=ApplicabilityCode.MANDATORY,
        monetary_unit_applicability_code=ApplicabilityCode.NOT_PERMITTED,
    )


@pytest.fixture
def duty_expressions(
    percent_or_amount: DutyExpression,
    plus_percent_or_amount: DutyExpression,
    plus_agri_component: DutyExpression,
    plus_amount_only: DutyExpression,
    supplementary_unit: DutyExpression,
    nothing: DutyExpression,
) -> Dict[int, DutyExpression]:
    return {
        d.sid: d
        for d in [
            percent_or_amount,
            plus_percent_or_amount,
            plus_agri_component,
            plus_amount_only,
            supplementary_unit,
            nothing,
        ]
    }


@pytest.fixture
def monetary_units() -> Dict[str, MonetaryUnit]:
    return {
        m.code: m
        for m in [
            factories.MonetaryUnitFactory(code="EUR"),
            factories.MonetaryUnitFactory(code="GBP"),
            factories.MonetaryUnitFactory(code="XEM"),
        ]
    }


@pytest.fixture
def measurement_units() -> Sequence[MeasurementUnit]:
    return [
        factories.MeasurementUnitFactory(code="KGM", abbreviation="kg"),
        factories.MeasurementUnitFactory(code="DTN", abbreviation="100 kg"),
        factories.MeasurementUnitFactory(code="MIL", abbreviation="1,000 p/st"),
    ]


@pytest.fixture
def unit_qualifiers() -> Sequence[MeasurementUnitQualifier]:
    return [
        factories.MeasurementUnitQualifierFactory(code="Z", abbreviation="lactic."),
    ]


@pytest.fixture
def measurements(
    measurement_units,
    unit_qualifiers,
) -> Dict[Tuple[str, Optional[str]], Measurement]:
    measurements = [
        *[
            factories.MeasurementFactory(
                measurement_unit=m,
                measurement_unit_qualifier=None,
            )
            for m in measurement_units
        ],
        factories.MeasurementFactory(
            measurement_unit=measurement_units[1],
            measurement_unit_qualifier=unit_qualifiers[0],
        ),
    ]
    return {
        (
            m.measurement_unit.code,
            m.measurement_unit_qualifier.code if m.measurement_unit_qualifier else None,
        ): m
        for m in measurements
    }


@pytest.fixture
def condition_duty_sentence_parser(
    duty_expressions: Dict[int, DutyExpression],
    monetary_units: Dict[str, MonetaryUnit],
    measurements: Dict[Tuple[str, Optional[str]], Measurement],
) -> DutySentenceParser:
    return DutySentenceParser(
        duty_expressions.values(),
        monetary_units.values(),
        measurements.values(),
        MeasureConditionComponent,
    )


@pytest.fixture
def get_component_data(duty_expressions, monetary_units, measurements) -> Callable:
    def getter(
        duty_expression_id,
        amount,
        monetary_unit_code,
        measurement_codes,
    ) -> Dict:
        return {
            "duty_expression": duty_expressions.get(duty_expression_id),
            "duty_amount": amount,
            "monetary_unit": monetary_units.get(monetary_unit_code),
            "component_measurement": measurements.get(measurement_codes),
        }

    return getter


@pytest.fixture(
    params=(
        ("4.000%", [(1, 4.0, None, None)]),
        ("1.230 EUR / kg", [(1, 1.23, "EUR", ("KGM", None))]),
        ("0.300 XEM / 100 kg / lactic.", [(1, 0.3, "XEM", ("DTN", "Z"))]),
        (
            "12.900% + 20.000 EUR / kg",
            [(1, 12.9, None, None), (4, 20.0, "EUR", ("KGM", None))],
        ),
        ("kg", [(99, None, None, ("KGM", None))]),
        ("100 kg", [(99, None, None, ("DTN", None))]),
        ("1.000 EUR", [(1, 1.0, "EUR", None)]),
        ("0.000% + AC", [(1, 0.0, None, None), (12, None, None, None)]),
    ),
    ids=[
        "simple_ad_valorem",
        "simple_specific_duty",
        "unit_with_qualifier",
        "multi_component_expression",
        "supplementary_unit",
        "supplementary_unit_with_numbers",
        "monetary_unit_without_measurement",
        "non_amount_expression",
    ],
)
def reversible_duty_sentence_data(request, get_component_data):
    """Duty sentence test cases that are syntactically correct and are also
    formatted correctly."""
    expected, component_data = request.param
    return expected, [get_component_data(*args) for args in component_data]


@pytest.fixture(
    params=(
        ("20.0 EUR/100kg", [(1, 20.0, "EUR", ("DTN", None))]),
        ("1.0 EUR/1000 p/st", [(1, 1.0, "EUR", ("MIL", None))]),
    ),
    ids=[
        "parses_without_spaces",
        "parses_without_commas",
    ],
)
def irreversible_duty_sentence_data(request, get_component_data):
    """Duty sentence test cases that are syntactically correct but are not in
    the canonical rendering format with spaces and commas in the correct
    places."""
    expected, component_data = request.param
    return expected, [get_component_data(*args) for args in component_data]


@pytest.fixture(
    params=(
        (
            (
                "0.000% + AC",
                [(1, 0.0, None, None), (12, None, None, None)],
            ),
            (
                "12.900% + 20.000 EUR / kg",
                [(1, 12.9, None, None), (4, 20.0, "EUR", ("KGM", None))],
            ),
        ),
    ),
)
def duty_sentence_x_2_data(request, get_component_data):
    """Duty sentence test cases that can be used to create a history of
    components."""
    history = []
    for version in request.param:
        expected, component_data = version
        history.append(
            (expected, [get_component_data(*args) for args in component_data]),
        )
    return history


@pytest.fixture()
def mocked_send_emails_apply_async():
    with patch(
        "notifications.tasks.send_emails_task.apply_async",
        return_value=MagicMock(id=factory.Faker("uuid4")),
    ) as mocked_delay:
        yield mocked_delay


@pytest.fixture()
def mocked_send_emails():
    with patch(
        "notifications.tasks.send_emails_task",
        return_value=MagicMock(id=factory.Faker("uuid4")),
    ) as mocked_delay:
        yield mocked_delay


@pytest.fixture(scope="function")
def packaged_workbasket_factory(queued_workbasket_factory):
    """
    Factory fixture to create a packaged workbasket.

    params:
    workbasket defaults to queued_workbasket_factory() which creates a
    Workbasket in the state QUEUED with an approved transaction and tracked models
    """

    def factory_method(workbasket=None, **kwargs):
        if not workbasket:
            workbasket = queued_workbasket_factory()
        with patch(
            "publishing.tasks.create_xml_envelope_file.apply_async",
            return_value=MagicMock(id=factory.Faker("uuid4")),
        ):
            packaged_workbasket = factories.QueuedPackagedWorkBasketFactory(
                workbasket=workbasket,
                **kwargs,
            )
        return packaged_workbasket

    return factory_method


@pytest.fixture(scope="function")
def published_envelope_factory(packaged_workbasket_factory, envelope_storage):
    """
    Factory fixture to create an envelope and update the packaged_workbasket
    envelope field.

    params:
    packaged_workbasket defaults to packaged_workbasket_factory() which creates a
    Packaged workbasket with a Workbasket in the state QUEUED
    with an approved transaction and tracked models
    """

    def factory_method(packaged_workbasket=None, **kwargs):
        if not packaged_workbasket:
            packaged_workbasket = packaged_workbasket_factory()

        with patch(
            "publishing.storages.EnvelopeStorage.save",
            wraps=MagicMock(side_effect=envelope_storage.save),
        ) as mock_save:
            envelope = factories.PublishedEnvelopeFactory(
                packaged_work_basket=packaged_workbasket,
                **kwargs,
            )
            mock_save.assert_called_once()

        packaged_workbasket.envelope = envelope
        packaged_workbasket.save()
        return envelope

    return factory_method


@pytest.fixture(scope="function")
def successful_envelope_factory(
    published_envelope_factory,
    mocked_send_emails_apply_async,
):
    """
    Factory fixture to create a successfully processed envelope and update the
    packaged_workbasket envelope field.

    params:
    packaged_workbasket defaults to packaged_workbasket_factory() which creates a
    Packaged workbasket with a Workbasket in the state QUEUED
    with an approved transaction and tracked models
    """

    def factory_method(**kwargs):
        envelope = published_envelope_factory(**kwargs)

        packaged_workbasket = PackagedWorkBasket.objects.get(
            envelope=envelope,
        )

        packaged_workbasket.begin_processing()
        assert packaged_workbasket.position == 0
        assert (
            packaged_workbasket.pk
            == PackagedWorkBasket.objects.currently_processing().pk
        )
        factories.LoadingReportFactory.create(packaged_workbasket=packaged_workbasket)
        packaged_workbasket.processing_succeeded()
        packaged_workbasket.save()
        assert packaged_workbasket.position == 0
        return envelope

    return factory_method


@pytest.fixture(scope="function")
def failed_envelope_factory(
    published_envelope_factory,
    mocked_send_emails_apply_async,
):
    """
    Factory fixture to create a successfully processed envelope and update the
    packaged_workbasket envelope field.

    params:
    packaged_workbasket defaults to packaged_workbasket_factory() which creates a
    Packaged workbasket with a Workbasket in the state QUEUED
    with an approved transaction and tracked models
    """

    def factory_method(**kwargs):
        envelope = published_envelope_factory(**kwargs)

        packaged_workbasket = PackagedWorkBasket.objects.get(
            envelope=envelope,
        )

        packaged_workbasket.begin_processing()
        assert packaged_workbasket.position == 0
        assert (
            packaged_workbasket.pk
            == PackagedWorkBasket.objects.currently_processing().pk
        )
        factories.LoadingReportFactory.create(packaged_workbasket=packaged_workbasket)

        packaged_workbasket.processing_failed()
        packaged_workbasket.save()
        assert packaged_workbasket.position == 0
        return envelope

    return factory_method


@pytest.fixture(scope="function")
def crown_dependencies_envelope_factory(successful_envelope_factory):
    """
    Factory fixture to create a crown dependencies envelope.

    params:
    packaged_workbasket defaults to packaged_workbasket_factory() which creates a
    Packaged workbasket with a Workbasket in the state QUEUED
    with an approved transaction and tracked models
    """

    def factory_method(**kwargs):
        envelope = successful_envelope_factory(**kwargs)

        packaged_workbasket = PackagedWorkBasket.objects.get(
            envelope=envelope,
        )
        return factories.CrownDependenciesEnvelopeFactory(
            packaged_work_basket=packaged_workbasket,
        )

    return factory_method
