from typing import List

import pytest
from pytest_django.asserts import assertQuerysetEqual

from common.exceptions import NoIdentifyingValuesGivenError
from common.models import TrackedModel
from common.tests import factories
from common.tests.models import TestModel1
from common.tests.models import TestModel2
from common.validators import UpdateType
from footnotes.models import FootnoteType
from regulations.models import Group
from regulations.models import Regulation

pytestmark = pytest.mark.django_db


def generate_model_history(factory, number=5, **kwargs) -> List:
    objects = []
    kwargs["update_type"] = kwargs.get("update_type", UpdateType.CREATE)
    current = factory(**kwargs)
    objects.append(current)
    kwargs["update_type"] = UpdateType.UPDATE
    kwargs["version_group"] = kwargs.get("version_group", current.version_group)
    for _ in range(number - 1):
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
            valid_between=date_ranges.current, update_type=UpdateType.UPDATE, **kwargs
        )

        all_models.append(active_model)

        all_models.extend(
            generate_model_history(
                factory,
                valid_between=date_ranges.future,
                update_type=UpdateType.UPDATE,
                **kwargs,
            )
        )

    return Models


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


def test_as_at(date_ranges):
    """
    Ensure only records active at a specific date are fetched.
    """

    pks = {
        factories.TestModel1Factory(valid_between=date_ranges.later).pk,
        factories.TestModel1Factory(valid_between=date_ranges.later).pk,
    }

    queryset = TestModel1.objects.as_at(date_ranges.later.lower)

    assert set(queryset.values_list("pk", flat=True)) == pks


def test_active(model1_with_history):
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
        TestModel1.objects.get_versions()

    with pytest.raises(NoIdentifyingValuesGivenError):
        TestModel2.objects.get_versions(sid=1)


def test_get_current_version(model1_with_history):
    """
    Ensure getting the current version works with a standard sid identifier.
    """
    model = model1_with_history.active_model

    assert TestModel1.objects.get_current_version(sid=model.sid) == model


def test_get_current_version_custom_identifier(model2_with_history):
    """
    Ensure getting the current version works with a custom identifier.
    """
    model = model2_with_history.active_model

    assert TestModel2.objects.get_current_version(custom_sid=model.custom_sid) == model


def test_get_latest_version(model1_with_history):
    """
    Ensure getting the latest version works with a standard sid identifier.
    """
    model = model1_with_history.all_models[-1]

    assert TestModel1.objects.get_latest_version(sid=model.sid) == model


def test_get_latest_version_custom_identifier(model2_with_history):
    """
    Ensure getting the latest version works with a custom identifier.
    """
    model = model2_with_history.all_models[-1]

    assert TestModel2.objects.get_latest_version(custom_sid=model.custom_sid) == model


def test_get_first_version(model1_with_history):
    """
    Ensure getting the first version works with a standard sid identifier.
    """
    model = model1_with_history.all_models[0]

    assert TestModel1.objects.get_first_version(sid=model.sid) == model


def test_get_first_version_custom_identifier(model2_with_history):
    """
    Ensure getting the first version works with a custom identifier.
    """
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
