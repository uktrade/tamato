from typing import List

import pytest

from common.exceptions import NoIdentifyingValuesGivenError
from common.models import TrackedModel
from common.tests import factories
from common.tests.models import TestModel1
from common.tests.models import TestModel2

pytestmark = pytest.mark.django_db


def generate_model_history(factory, number=5, **kwargs) -> List:
    objects = []
    current = factory(**kwargs)
    objects.append(current)
    for _ in range(number - 1):
        kwargs["predecessor"] = current
        current = factory(**kwargs)
        objects.append(current)

    return objects


def model_with_history(factory, date_ranges, **kwargs):
    class Models:
        """
        A convenient system to store tracked models.

        Creates a number of historic models for both test model types.

        Creates an active model for each test model type.

        Then creates a number of future models for each type as well.
        """

        all_models = generate_model_history(
            factory, valid_between=date_ranges.earlier, **kwargs
        )

        active_model = factory(
            predecessor=all_models[-1], valid_between=date_ranges.current, **kwargs
        )

        all_models.append(active_model)

        all_models.extend(
            generate_model_history(
                factory,
                predecessor=active_model,
                valid_between=date_ranges.future,
                **kwargs,
            )
        )

    return Models


@pytest.fixture
def model1_with_history(date_ranges):
    return model_with_history(factories.TestModel1Factory, date_ranges, sid=1)


@pytest.fixture
def model2_with_history(date_ranges):
    return model_with_history(factories.TestModel2Factory, date_ranges, custom_sid=1)


@pytest.mark.freeze_time("2020-08-01")
def test_get_current(model1_with_history, model2_with_history):
    """
    Ensure only the most recent records are fetched.
    """
    latest_models = TrackedModel.objects.current()

    assert latest_models.count() == 2
    assert set(latest_models.values_list("pk", flat=True)) == {
        model1_with_history.all_models[-1].pk,
        model2_with_history.all_models[-1].pk,
    }


def test_since_transaction():
    """
    Ensure all records since a transaction are fetched.
    """
    for _ in range(5):
        workbasket = factories.TransactionFactory().workbasket
        factories.TestModel1Factory(workbasket=workbasket)
        factories.TestModel2Factory(workbasket=workbasket)

    transaction = factories.TransactionFactory()

    recent_transactions = set()

    for _ in range(2):
        workbasket = factories.TransactionFactory().workbasket
        recent_transactions.add(factories.TestModel1Factory(workbasket=workbasket).pk)
        recent_transactions.add(factories.TestModel2Factory(workbasket=workbasket).pk)

    since_transaction = TrackedModel.objects.since_transaction(transaction.pk)

    assert set(since_transaction.values_list("pk", flat=True)) == recent_transactions


def test_as_at(model1_with_history, date_ranges):
    """
    Ensure only records active at a specific date are fetched.
    """

    pks = {
        factories.TestModel1Factory(valid_between=date_ranges.normal).pk,
        factories.TestModel1Factory(valid_between=date_ranges.normal).pk,
    }

    queryset = TestModel1.objects.as_at(date_ranges.normal.lower)

    assert set(queryset.values_list("pk", flat=True)) == pks


@pytest.mark.freeze_time("2020-08-01")
def test_active(model1_with_history, date_ranges):
    """
    Ensure only the currently active records are fetched.
    """
    queryset = TestModel1.objects.active()

    assert set(queryset.values_list("pk", flat=True)) == {
        model1_with_history.active_model.pk
    }


def test_get_version_raises_error():
    """
    Ensure that trying to get a specific version raises an error if no identifiers given.
    """
    with pytest.raises(NoIdentifyingValuesGivenError):
        TestModel1.objects.get_version()

    with pytest.raises(NoIdentifyingValuesGivenError):
        TestModel2.objects.get_version(sid=1)


@pytest.mark.freeze_time("2020-08-01")
def test_get_current_version(date_ranges, model1_with_history):
    """
    Ensure getting the current version works with a standard sid identifier.
    """
    model = model1_with_history.active_model

    assert TestModel1.objects.get_current_version(sid=model.sid) == model


@pytest.mark.freeze_time("2020-08-01")
def test_get_current_version_custom_identifier(date_ranges, model2_with_history):
    """
    Ensure getting the current version works with a custom identifier.
    """
    model = model2_with_history.active_model

    assert TestModel2.objects.get_current_version(custom_sid=model.custom_sid) == model


def test_get_latest_version(date_ranges, model1_with_history):
    """
    Ensure getting the latest version works with a standard sid identifier.
    """
    model = model1_with_history.all_models[-1]

    assert TestModel1.objects.get_latest_version(sid=model.sid) == model


def test_get_latest_version_custom_identifier(date_ranges, model2_with_history):
    """
    Ensure getting the latest version works with a custom identifier.
    """
    model = model2_with_history.all_models[-1]

    assert TestModel2.objects.get_latest_version(custom_sid=model.custom_sid) == model


def test_get_first_version(date_ranges, model1_with_history):
    """
    Ensure getting the first version works with a standard sid identifier.
    """
    model = model1_with_history.all_models[0]

    assert TestModel1.objects.get_first_version(sid=model.sid) == model


def test_get_first_version_custom_identifier(date_ranges, model2_with_history):
    """
    Ensure getting the first version works with a custom identifier.
    """
    model = model2_with_history.all_models[0]

    assert TestModel2.objects.get_first_version(custom_sid=model.custom_sid) == model
