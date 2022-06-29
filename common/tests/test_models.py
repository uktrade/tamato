from unittest.mock import patch
from urllib.parse import urlparse

import factory
import freezegun
import pytest
from pytest_django.asserts import assertQuerysetEqual  # type: ignore

import common.exceptions
import workbaskets.models
from common.exceptions import NoIdentifyingValuesGivenError
from common.models import TrackedModel
from common.models.transactions import Transaction
from common.models.transactions import TransactionPartition
from common.models.utils import LazyString
from common.tests import factories
from common.tests import models
from common.tests.factories import EnvelopeFactory
from common.tests.factories import TestModel1Factory
from common.tests.models import TestModel1
from common.tests.models import TestModel2
from common.tests.models import TestModel3
from common.tests.util import assert_transaction_order
from common.validators import UpdateType
from footnotes.models import FootnoteType
from measures.models import MeasureCondition
from regulations.models import Group
from regulations.models import Regulation
from taric.models import Envelope
from workbaskets.tasks import check_workbasket_sync

pytestmark = pytest.mark.django_db


@pytest.fixture
def sample_model() -> models.TestModel1:
    return factories.TestModel1Factory.create()


def test_get_current(model1_with_history, model2_with_history):
    """Ensure only the most recent records are fetched."""
    latest_models = TrackedModel.objects.latest_approved()

    assert latest_models.count() == 2
    assert set(latest_models.values_list("pk", flat=True)) == {
        model1_with_history.all_models[-1].pk,
        model2_with_history.all_models[-1].pk,
    }


def test_versions_up_to(model1_with_history):
    """Ensure that versions_up_to returns all versions that are approved up to
    and including the past transaction, not future ones and not just the
    latest."""
    for index, model in enumerate(model1_with_history.all_models):
        versions = TestModel1.objects.versions_up_to(model.transaction)
        assert versions.count() == index + 1
        assert versions.last() == model


def test_as_at(date_ranges, validity_factory):
    """Ensure only records active at a specific date are fetched."""
    pks = {
        validity_factory.create(valid_between=date_ranges.later).pk,
        validity_factory.create(valid_between=date_ranges.later).pk,
    }
    Model = validity_factory._meta.get_model_class()

    queryset = Model.objects.as_at(date_ranges.later.lower)

    assert set(queryset.values_list("pk", flat=True)) == pks


def test_as_at_today(model1_with_history):
    """Ensure only the currently active records are fetched."""
    queryset = TestModel1.objects.as_at_today()

    assert set(queryset.values_list("pk", flat=True)) == {
        model1_with_history.active_model.pk,
    }


def test_get_version_raises_error():
    """Ensure that trying to get a specific version raises an error if no
    identifiers given."""
    with pytest.raises(NoIdentifyingValuesGivenError):
        TestModel1.objects.get_versions()

    with pytest.raises(NoIdentifyingValuesGivenError):
        TestModel2.objects.get_versions(sid=1)


def test_get_latest_version(model1_with_history):
    """Ensure getting the latest version works with a standard sid
    identifier."""
    model = model1_with_history.all_models[-1]

    assert TestModel1.objects.get_latest_version(sid=model.sid) == model


def test_get_latest_version_custom_identifier(model2_with_history):
    """Ensure getting the latest version works with a custom identifier."""
    model = model2_with_history.all_models[-1]

    assert TestModel2.objects.get_latest_version(custom_sid=model.custom_sid) == model


def test_get_first_version(model1_with_history):
    """Ensure getting the first version works with a standard sid identifier."""
    model = model1_with_history.all_models[0]

    assert TestModel1.objects.get_first_version(sid=model.sid) == model


def test_get_first_version_custom_identifier(model2_with_history):
    """Ensure getting the first version works with a custom identifier."""
    model = model2_with_history.all_models[0]

    assert TestModel2.objects.get_first_version(custom_sid=model.custom_sid) == model


def test_trackedmodel_can_attach_record_codes(workbasket):
    tx = workbasket.new_transaction()

    with tx:
        # Note:  regulation.Regulation implicitly creates a regulation.Group as well!
        factories.RegulationFactory.create()
        factories.FootnoteTypeFactory.create()

    tracked_models = (
        TrackedModel.objects.annotate_record_codes()
        .select_related()
        .filter(transaction=tx)
    )

    expected_models = [
        (tx.pk, Group, "150", "00"),
        (tx.pk, Regulation, "285", "00"),
        (tx.pk, FootnoteType, "100", "00"),
    ]

    assertQuerysetEqual(
        tracked_models,
        expected_models,
        transform=lambda o: (
            o.transaction.pk,
            o.__class__,
            o.record_code,
            o.subrecord_code,
        ),
        ordered=False,
    )


def test_get_latest_relation_with_latest_links(
    model1_with_history,
    django_assert_num_queries,
):
    """Assert that using `.with_latest_links` should allow a TrackedModel to
    retrieve the current version of a relation without any extra queries."""
    oldest_link = model1_with_history.all_models[0]
    latest_link = model1_with_history.all_models[-1]

    factories.TestModel3Factory.create(linked_model=oldest_link)

    with django_assert_num_queries(1):
        instance = TestModel3.objects.all().with_latest_links()[0]
        fetched_oldest_link = instance.linked_model
        fetched_latest_link = instance.linked_model.current_version

    assert oldest_link.pk == fetched_oldest_link.pk
    assert latest_link.pk == fetched_latest_link.pk


def test_get_latest_relation_without_latest_links(
    model1_with_history,
    django_assert_num_queries,
):
    """
    Assert that without using `.with_latest_link` requires a Tracked Model to
    use 4 queries to get the current version of a relation.

    Finding the current version of an object requires 4 queries:

    - Get the originating object as a starting point (e.g. start = TrackedModel.objects.get(pk=1))
    - Get the related object (e.g. related = start.link)
    - Get the related objects version group (e.g. group = related.version_group)
    - Get the current version (e.g. current = group.current_version)
    """
    oldest_link = model1_with_history.all_models[0]
    latest_link = model1_with_history.all_models[-1]

    factories.TestModel3Factory.create(linked_model=oldest_link)

    with django_assert_num_queries(4):
        instance = TestModel3.objects.all().select_related("linked_model")[0]
        fetched_oldest_link = instance.linked_model
        fetched_latest_link = instance.linked_model.current_version

    assert oldest_link == fetched_oldest_link
    assert latest_link == fetched_latest_link


def test_current_version(sample_model):
    assert sample_model.current_version == sample_model

    version_group = sample_model.version_group
    version_group.current_version = None
    version_group.save()

    with pytest.raises(models.TestModel1.DoesNotExist):
        sample_model.current_version


def test_save(sample_model):
    assert sample_model.current_version == sample_model

    with pytest.raises(common.exceptions.IllegalSaveError):
        sample_model.name = "fails"
        sample_model.save()

    sample_model.name = "succeeds"
    sample_model.save(force_write=True)


@pytest.mark.parametrize(
    ("initial_dates"),
    ("normal", "no_end"),
    ids=("has_end_date", "has_no_end_date"),
)
@pytest.mark.parametrize(
    ("termination_range"),
    ("earlier", "overlap_normal", "later"),
    ids=("before_start", "during_validity", "after_existing_end"),
)
def test_terminate(
    validity_factory,
    date_ranges,
    workbasket,
    termination_range,
    initial_dates,
):
    model = validity_factory.create(valid_between=getattr(date_ranges, initial_dates))
    termination_date = getattr(date_ranges, termination_range).upper
    terminated_model = model.terminate(workbasket, termination_date)

    if terminated_model.update_type == UpdateType.DELETE:
        assert terminated_model.valid_between.lower >= termination_date
    else:
        assert terminated_model.valid_between.upper_inf is False
        assert terminated_model.valid_between.upper <= termination_date


def test_new_version_uses_passed_transaction(sample_model):
    transaction_count = Transaction.objects.count()
    new_transaction = sample_model.transaction.workbasket.new_transaction()
    new_model = sample_model.new_version(
        sample_model.transaction.workbasket,
        transaction=new_transaction,
    )
    assert new_model.transaction == new_transaction
    assert Transaction.objects.count() == transaction_count + 1


def test_new_version_works_for_all_models(trackedmodel_factory):
    model = trackedmodel_factory.create()
    model.new_version(model.transaction.workbasket)


def test_new_version_retains_related_objects(sample_model):
    description = factories.TestModelDescription1Factory(
        described_record=sample_model,
    )
    assert sample_model.descriptions.get() == description

    new_model = sample_model.new_version(
        sample_model.transaction.workbasket,
    )
    assert new_model.descriptions.get() == description


def test_current_as_of(sample_model):
    transaction = factories.UnapprovedTransactionFactory.create()

    with transaction:
        unapproved_version = factories.TestModel1Factory.create(
            sid=sample_model.sid,
            version_group=sample_model.version_group,
        )

    assert models.TestModel1.objects.latest_approved().get().pk == sample_model.pk
    assert (
        models.TestModel1.objects.approved_up_to_transaction(transaction).get().pk
        == unapproved_version.pk
    )


def test_create_with_description():
    """Tests that when calling ``create`` on a described object, an associated
    description is created with the correct data."""

    # Get the data we need for the model, except the transaction needs to exist
    # and we don't want a version group as it will be added on save.
    model_data = factory.build(
        dict,
        FACTORY_CLASS=factories.TestModel1Factory,
        transaction=factories.ApprovedTransactionFactory(),
        version_group=None,
        description=factories.short_description(),
    )
    model = TestModel1.create(**model_data)

    description = model.get_descriptions().get()
    assert description.validity_start == model.valid_between.lower
    assert description.transaction == model.transaction
    assert description.update_type == model.update_type
    assert description.described_record == model


def test_get_descriptions(sample_model):
    descriptions = {
        factories.TestModelDescription1Factory.create(described_record=sample_model)
        for _ in range(2)
    }
    assert set(sample_model.get_descriptions()) == descriptions


def test_get_descriptions_with_update(sample_model, valid_user):
    description = factories.TestModelDescription1Factory.create(
        described_record=sample_model,
    )
    workbasket = factories.WorkBasketFactory.create()
    new_description = description.new_version(workbasket)

    description_queryset = sample_model.get_descriptions()
    assert description in description_queryset
    assert new_description not in description_queryset

    description_queryset = sample_model.get_descriptions(
        transaction=new_description.transaction,
    )

    assert new_description in description_queryset
    assert description not in description_queryset

    check_workbasket_sync(workbasket)
    workbasket.submit_for_approval()
    with patch(
        "exporter.tasks.upload_workbaskets.delay",
    ):
        workbasket.approve(valid_user.pk, "SEED_FIRST")
    description_queryset = sample_model.get_descriptions()

    assert new_description in description_queryset
    assert description not in description_queryset


def test_get_description_dates(description_factory, date_ranges):
    """Verify that description models know how to calculate their end dates,
    which should be up until the next description model starts or inifnite if
    there is no later one."""
    early_description = description_factory.create(
        validity_start=date_ranges.adjacent_earlier.lower,
    )

    unrelated_description = description_factory.create(
        # Note this doesn't share a described_record with above.
        validity_start=date_ranges.adjacent_earlier.upper,
    )

    described_record = early_description.get_described_object()
    current_description = description_factory.create(
        **{early_description.described_object_field.name: described_record},
        validity_start=date_ranges.normal.lower,
    )

    future_description = description_factory.create(
        **{early_description.described_object_field.name: described_record},
        validity_start=date_ranges.adjacent_later.lower,
    )

    objects = (
        type(early_description)
        .objects.filter(
            **{early_description.described_object_field.name: described_record},
        )
        .with_end_date()
    )

    earlier = objects.as_at(date_ranges.adjacent_earlier.upper).get()
    assert earlier.validity_end == date_ranges.adjacent_earlier.upper
    assert earlier == early_description

    current = objects.as_at(date_ranges.normal.upper).get()
    assert current.validity_end == date_ranges.normal.upper
    assert current == current_description

    future = objects.as_at(date_ranges.adjacent_later.upper).get()
    assert future.validity_end is None
    assert future == future_description


def test_trackedmodel_get_url(trackedmodel_factory):
    """Verify get_url() returns something sensible and doesn't crash."""
    instance = trackedmodel_factory.create()
    url = instance.get_url()

    if url is None:
        # None is returned for models that have no URL
        return

    if instance.url_suffix:
        assert instance.url_suffix in url

    assert len(url)

    # Verify URL is not local
    assert not urlparse(url).netloc


@pytest.mark.parametrize(
    "factory",
    [
        factories.AdditionalCodeFactory,
        factories.CertificateFactory,
        factories.FootnoteFactory,
        factories.GeographicalAreaFactory,
    ],
)
def test_trackedmodel_get_description_create_url(factory):
    """Verify get_url() returns something for creating descriptions."""
    instance = factory.create()
    url = instance.get_url("description-create")

    assert url


@pytest.mark.parametrize(
    "factory",
    [
        factories.AdditionalCodeFactory,
        factories.FootnoteFactory,
        factories.MeasureFactory,
        factories.RegulationFactory,
    ],
)
def test_trackedmodel_get_create_url(factory):
    instance = factory.create()
    url = instance.get_url("create")

    assert url


def test_trackedmodel_str(trackedmodel_factory):
    """Verify no __str__ methods of TrackedModel classes crash or return non-
    strings."""
    instance = trackedmodel_factory.create()
    result = instance.__str__()

    assert isinstance(result, str)
    assert len(result.strip())


@pytest.mark.django_db(transaction=True, reset_sequences=True)
def test_trackedmodel_base_str():
    """
    Verify TrackedModel base class can stringify without crashing, so that.

    .trackedmodel_ptr will work on TrackedModel subclasses.
    """
    model = factories.TestModel1Factory.create()
    trackedmodel = model.trackedmodel_ptr

    result = str(trackedmodel)

    assert f"pk={trackedmodel.pk}" == result


def test_copy(trackedmodel_factory, approved_transaction):
    """Verify that a copy of a TrackedModel is a new instance with different
    primary key and version group."""
    instance: TrackedModel = trackedmodel_factory.create()
    copy = instance.copy(approved_transaction)

    assert copy.pk != instance.pk
    assert copy.version_group != instance.version_group


@pytest.mark.parametrize(
    ("starting_sid", "expected_next_sid"),
    (
        (0, 1),
        (10, 11),
    ),
)
def test_copy_increments_sid_fields(starting_sid, expected_next_sid):
    instance = factories.TestModel1Factory.create(sid=starting_sid)
    copy = instance.copy(factories.ApprovedTransactionFactory())

    assert copy.sid == expected_next_sid


def test_copy_also_copies_dependents():
    desc = factories.TestModelDescription1Factory.create()
    copy = desc.described_record.copy(factories.ApprovedTransactionFactory())

    assert copy.descriptions.count() == 1
    assert copy.descriptions.get() != desc
    assert copy.descriptions.get().description == desc.description


def test_save_single_draft_transaction_updates(unordered_transactions):
    """Verify that save_draft correctly sets the order and partition
    correctly."""
    unordered_transactions.new_transaction.save_draft(workbaskets.models.REVISION_ONLY)

    assert (
        unordered_transactions.new_transaction.partition
        == TransactionPartition.REVISION
    )
    assert (
        unordered_transactions.existing_transaction.order + 1
        == unordered_transactions.new_transaction.order
    )
    assert_transaction_order(Transaction.objects.all())


def test_save_drafts_transaction_updates(unordered_transactions):
    """Verify that save_drafts correctly sets the order and partition
    correctly."""
    Transaction.objects.filter(
        pk=unordered_transactions.new_transaction.pk,
    ).save_drafts(workbaskets.models.REVISION_ONLY)
    unordered_transactions.new_transaction.refresh_from_db()

    assert set(Transaction.objects.values_list("partition", flat=True)) == {
        TransactionPartition.REVISION.value,
    }
    assert (
        unordered_transactions.existing_transaction.order + 1
        == unordered_transactions.new_transaction.order
    )
    assert_transaction_order(Transaction.objects.all())


def test_structure_description(trackedmodel_factory):
    model = trackedmodel_factory.create()
    description = model.structure_description

    if description:
        assert type(description) == str

    if "structure_description" in type(model).__dict__:
        pass
    elif hasattr(type(model), "descriptions") and model.get_descriptions().last():
        assert description == model.get_descriptions().last().description
    elif hasattr(type(model), "description"):
        assert description == model.description
    else:
        assert description == None


def test_described(description_factory):
    description = description_factory.create()
    described = description.get_described_object()

    assert described.get_description() == description


def test_get_url_pattern_name_prefix():
    assert TestModel1.get_url_pattern_name_prefix() == "test_model1"


@pytest.fixture(scope="session")
def test_numeric_sid_iteration():
    assert isinstance(TestModel1.sid.field, common.fields.NumericSID)

    sids = [TestModel1Factory.create().sid for i in range(3)]

    assert sids == [1, 2, 3]


def test_copy_related_model():
    measure = factories.MeasureFactory.create()
    goods_nomenclature = factories.GoodsNomenclatureFactory.create()
    workbasket = factories.ApprovedWorkBasketFactory.create()

    copied_measure = measure.copy(
        workbasket.new_transaction(),
        goods_nomenclature=goods_nomenclature,
    )

    assert copied_measure.goods_nomenclature == goods_nomenclature


@pytest.mark.parametrize(
    "conditions",
    [
        ([]),
        (None),
    ],
)
def test_copy_empty_for_related_models(conditions):
    measure = factories.MeasureFactory.create()
    condition = factories.MeasureConditionFactory.create(dependent_measure=measure)
    workbasket = factories.ApprovedWorkBasketFactory.create()

    copied_measure = measure.copy(workbasket.new_transaction(), conditions=conditions)

    assert copied_measure.conditions.count() == 0


def test_copy_fk_related_models():
    measure = factories.MeasureFactory.create()
    workbasket = factories.ApprovedWorkBasketFactory.create()
    code = factories.MeasureConditionCodeFactory.create()
    transaction = workbasket.new_transaction()
    condition_data = {
        "transaction": transaction,
        "update_type": UpdateType.CREATE,
        "sid": "1",
        "component_sequence_number": 1,
        "condition_code_id": code.pk,
    }

    copied_measure = measure.copy(
        transaction,
        conditions=[MeasureCondition(**condition_data)],
    )

    assert copied_measure.conditions.count() == 1


def test_copy_nested_fk():
    measure = factories.MeasureFactory.create()
    workbasket = factories.ApprovedWorkBasketFactory.create()
    transaction = workbasket.new_transaction()
    factories.MeasureConditionFactory.create(
        transaction=transaction,
        dependent_measure=measure,
    )
    condition_code = factories.MeasureConditionCodeFactory()

    copied_measure = measure.copy(
        transaction,
        conditions__condition_code=condition_code,
    )

    assert copied_measure.conditions.first().condition_code == condition_code


def test_copy_nested_field():
    measure = factories.MeasureFactory.create()
    workbasket = factories.ApprovedWorkBasketFactory.create()
    transaction = workbasket.new_transaction()
    factories.MeasureConditionFactory.create(
        transaction=transaction,
        dependent_measure=measure,
    )

    copied_measure = measure.copy(
        transaction,
        conditions__component_sequence_number=999,
    )

    assert copied_measure.conditions.first().component_sequence_number == 999


def test_copy_nested_field_two_levels_deep():
    measure = factories.MeasureFactory.create()
    workbasket = factories.ApprovedWorkBasketFactory.create()
    transaction = workbasket.new_transaction()
    condition = factories.MeasureConditionFactory.create(
        transaction=transaction,
        dependent_measure=measure,
    )
    factories.MeasureConditionComponentFactory.create(
        transaction=transaction,
        condition=condition,
        duty_amount=1,
    )

    measure.conditions.first().components.first().duty_amount
    copied_measure = measure.copy(
        transaction,
        conditions__components__duty_amount=0,
    )

    assert copied_measure.conditions.first().components.first().duty_amount == 0


def test_transaction_summary(approved_transaction):
    """Verify that transaction.summary returns a LazyString which evaluates to a
    string with the expected fields."""
    # It's tricky to test lazy evaluation here, verifying an instance of LazyString works as a stand-in.
    assert isinstance(approved_transaction.summary, LazyString)

    expected_summary = (
        f"transaction: {approved_transaction.partition}, {approved_transaction.pk} "
        f"in workbasket: {approved_transaction.workbasket.status}, {approved_transaction.workbasket.pk}"
    )

    assert str(approved_transaction.summary) == expected_summary


@freezegun.freeze_time("2023-01-01")
@pytest.mark.parametrize(
    "year,first_envelope_id,next_envelope_id",
    [
        (2023, "230001", "230002"),
        (2023, "239998", "239999"),
    ],
)
def test_next_envelope_id(year, first_envelope_id, next_envelope_id):
    """Verify that envelope ID is made up of two digits of the year and a 4
    digit counter starting from 0001."""
    with freezegun.freeze_time(f"{year}-01-01"):
        assert EnvelopeFactory.create(envelope_id=first_envelope_id)
        assert Envelope.next_envelope_id() == next_envelope_id


def test_next_envelope_id_overflow():
    """Since the counter contains 4 digits, 9999 envelopes can be created a
    year, attempting to create more should raise a ValueError."""

    with freezegun.freeze_time("2023-01-01"):
        assert EnvelopeFactory.create(envelope_id="239999").envelope_id == "239999"

        with pytest.raises(ValueError):
            Envelope.next_envelope_id()
