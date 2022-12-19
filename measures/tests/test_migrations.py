from datetime import date
from datetime import timedelta

import pytest
from psycopg2._range import DateTimeTZRange

from common.tests.factories import ApprovedWorkBasketFactory
from common.tests.factories import DutyExpressionFactory
from common.tests.factories import GeographicalAreaFactory
from common.tests.factories import GoodsNomenclatureFactory
from common.tests.factories import MeasureTypeFactory
from common.tests.factories import RegulationFactory
from common.tests.factories import RegulationGroupFactory


@pytest.mark.django_db()
def test_add_back_deleted_measures(migrator, setup_content_types):
    from common.models.transactions import TransactionPartition

    """Ensures that the initial migration works."""
    old_state = migrator.apply_initial_migration(
        (
            "measures",
            "0011_pre_migration_dependencies",
        ),
    )

    setup_content_types(old_state.apps)

    # setup
    target_workbasket_id = 545

    measurement_class = old_state.apps.get_model("measures", "Measure")

    assert measurement_class.objects.filter(sid=20194965).exists() is False
    assert measurement_class.objects.filter(sid=20194966).exists() is False
    assert measurement_class.objects.filter(sid=20194967).exists() is False

    # mock up workbasket
    new_work_basket = ApprovedWorkBasketFactory.create(id=target_workbasket_id).save()

    # create the three goods
    goods_1 = GoodsNomenclatureFactory.create(item_id="0306920000").save(
        force_write=True,
    )
    goods_2 = GoodsNomenclatureFactory.create(item_id="0307190000").save(
        force_write=True,
    )
    goods_3 = GoodsNomenclatureFactory.create(item_id="0307490000").save(
        force_write=True,
    )

    # create the geo area
    new_geographical_area = GeographicalAreaFactory.create(sid=146).save(
        force_write=True,
    )

    # create the regulation group
    new_regulation_group = RegulationGroupFactory.create(
        valid_between=DateTimeTZRange(
            date.today() + timedelta(days=-1000),
            date.today() + timedelta(days=1000),
        ),
    ).save(force_write=True)

    # create the regulation
    new_regulation = RegulationFactory.create(
        valid_between=DateTimeTZRange(
            date.today() + timedelta(days=-1000),
            date.today() + timedelta(days=1000),
        ),
        regulation_group=new_regulation_group,
        regulation_id="C2100006",
        approved=True,
    ).save(force_write=True)

    # create the measure type
    new_measure_type = MeasureTypeFactory.create(sid=142).save(force_write=True)

    # create the duty expression
    new_duty_expression = DutyExpressionFactory.create(sid=1).save(force_write=True)

    # at this point all the appropriate elements are available within the database for the migration to create the
    # measures and conditions

    # run fix migration
    new_state = migrator.apply_tested_migration(
        ("measures", "0012_add_back_three_missing_measures_already_published"),
    )

    measurement_class = new_state.apps.get_model("measures", "Measure")

    measures_ids_to_check = [20194965, 20194966, 20194967]

    for measure_id_to_check in measures_ids_to_check:
        # we should be able to get the measurements from the database now
        assert (
            measurement_class.objects.filter(sid=measure_id_to_check).exists() is True
        )
        assert measurement_class.objects.filter(sid=measure_id_to_check).count() == 1
        measure_to_check = measurement_class.objects.get(sid=measure_id_to_check)
        # verify the transactions are on the correct partition
        assert measure_to_check.transaction.partition == TransactionPartition.REVISION
        # verify that the current version is as expected
        assert (
            measure_to_check.version_group.current_version_id
            == measure_to_check.trackedmodel_ptr_id
        )

    # verify that the current version is correct

    migrator.reset()


@pytest.mark.django_db()
def test_add_back_deleted_measures_fails_silently_if_data_not_present(
    migrator,
    setup_content_types,
):
    """Ensures that the initial migration works when no data to create measures
    are present, for local dev etc."""

    old_state = migrator.apply_initial_migration(
        (
            "measures",
            "0011_pre_migration_dependencies",
        ),
    )

    setup_content_types(old_state.apps)

    measurement_class = old_state.apps.get_model("measures", "Measure")

    assert measurement_class.objects.filter(sid=20194965).exists() is False
    assert measurement_class.objects.filter(sid=20194966).exists() is False
    assert measurement_class.objects.filter(sid=20194967).exists() is False

    # run fix migration
    new_state = migrator.apply_tested_migration(
        ("measures", "0012_add_back_three_missing_measures_already_published"),
    )

    measurement_class = new_state.apps.get_model("measures", "Measure")

    # we not get records, but also not get an exception
    assert measurement_class.objects.filter(sid=20194965).exists() is False
    assert measurement_class.objects.filter(sid=20194966).exists() is False
    assert measurement_class.objects.filter(sid=20194967).exists() is False

    migrator.reset()
