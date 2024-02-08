from datetime import date
from datetime import timedelta

import pytest
from psycopg2._range import DateTimeTZRange

from common.validators import ApplicabilityCode
from common.validators import UpdateType
from measures.validators import ImportExportCode
from measures.validators import MeasureExplosionLevel
from measures.validators import MeasureTypeCombination
from measures.validators import OrderNumberCaptureCode
from workbaskets.validators import WorkflowStatus


@pytest.mark.django_db()
def test_add_back_deleted_measures(migrator, date_ranges):
    from common.models.transactions import TransactionPartition

    """Ensures that the initial migration works."""
    old_state = migrator.apply_initial_migration(
        (
            "measures",
            "0011_pre_migration_dependencies",
        ),
    )

    # setup
    DutyExpression = old_state.apps.get_model("measures", "DutyExpression")
    ContentType = old_state.apps.get_model("contenttypes", "ContentType")
    GeographicalArea = old_state.apps.get_model("geo_areas", "GeographicalArea")
    GoodsNomenclature = old_state.apps.get_model("commodities", "GoodsNomenclature")
    Measure = old_state.apps.get_model("measures", "Measure")
    MeasureType = old_state.apps.get_model("measures", "MeasureType")
    MeasureTypeSeries = old_state.apps.get_model("measures", "MeasureTypeSeries")
    Regulation = old_state.apps.get_model("regulations", "Regulation")
    Group = old_state.apps.get_model("regulations", "Group")
    Transaction = old_state.apps.get_model("common", "Transaction")
    User = old_state.apps.get_model("common", "User")
    WorkBasket = old_state.apps.get_model("workbaskets", "WorkBasket")
    VersionGroup = old_state.apps.get_model("common", "VersionGroup")

    goods_content_type = ContentType.objects.get(model="goodsnomenclature")
    geo_area_content_type = ContentType.objects.get(model="geographicalarea")
    regulation_group_content_type = ContentType.objects.get(model="group")
    regulation_content_type = ContentType.objects.get(model="regulation")
    measure_series_content_type = ContentType.objects.get(model="measuretypeseries")
    measure_type_content_type = ContentType.objects.get(model="measuretype")
    duty_expression_content_type = ContentType.objects.get(model="dutyexpression")

    assert not Measure.objects.filter(sid=20194965).exists()
    assert not Measure.objects.filter(sid=20194966).exists()
    assert not Measure.objects.filter(sid=20194967).exists()

    # mock up workbasket
    user = User.objects.create()
    target_workbasket_id = 545
    workbasket = WorkBasket.objects.create(
        id=target_workbasket_id,
        author=user,
        approver=user,
        status=WorkflowStatus.QUEUED,
    )
    transaction = Transaction.objects.create(
        workbasket=workbasket,
        order=1,
        partition=TransactionPartition.REVISION,
        composite_key=str(workbasket.id)
        + "-"
        + "1"
        + "-"
        + str(TransactionPartition.REVISION),
    )

    # create the three goods
    goods_1 = GoodsNomenclature.objects.create(
        item_id="0306920000",
        update_type=UpdateType.CREATE,
        transaction=transaction,
        version_group=VersionGroup.objects.create(),
        valid_between=date_ranges.no_end,
        statistical=False,
        polymorphic_ctype=goods_content_type,
    )
    version_group = goods_1.version_group
    version_group.current_version_id = goods_1.id
    version_group.save()

    goods_2 = GoodsNomenclature.objects.create(
        item_id="0307190000",
        update_type=UpdateType.CREATE,
        transaction=transaction,
        version_group=VersionGroup.objects.create(),
        valid_between=date_ranges.no_end,
        statistical=False,
        polymorphic_ctype=goods_content_type,
    )
    version_group = goods_2.version_group
    version_group.current_version_id = goods_2.id
    version_group.save()

    goods_3 = GoodsNomenclature.objects.create(
        item_id="0307490000",
        update_type=UpdateType.CREATE,
        transaction=transaction,
        version_group=VersionGroup.objects.create(),
        valid_between=date_ranges.no_end,
        statistical=False,
        polymorphic_ctype=goods_content_type,
    )
    version_group = goods_3.version_group
    version_group.current_version_id = goods_3.id
    version_group.save()

    # create the geo area
    new_geographical_area = GeographicalArea.objects.create(
        sid=146,
        area_id="CA",
        area_code=0,
        update_type=UpdateType.CREATE,
        transaction=transaction,
        version_group=VersionGroup.objects.create(),
        valid_between=date_ranges.no_end,
        polymorphic_ctype=geo_area_content_type,
    )
    version_group = new_geographical_area.version_group
    version_group.current_version_id = new_geographical_area.id
    version_group.save()

    # create the regulation group
    new_regulation_group = Group.objects.create(
        update_type=UpdateType.CREATE,
        transaction=transaction,
        version_group=VersionGroup.objects.create(),
        valid_between=DateTimeTZRange(
            date.today() + timedelta(days=-1000),
            date.today() + timedelta(days=1000),
        ),
        polymorphic_ctype=regulation_group_content_type,
    )
    version_group = new_regulation_group.version_group
    version_group.current_version_id = new_regulation_group.id
    version_group.save()

    # create the regulation
    new_regulation = Regulation.objects.create(
        regulation_group=new_regulation_group,
        regulation_id="C2100006",
        approved=True,
        valid_between=DateTimeTZRange(
            date.today() + timedelta(days=-1000),
            date.today() + timedelta(days=1000),
        ),
        update_type=UpdateType.CREATE,
        transaction=transaction,
        version_group=VersionGroup.objects.create(),
        polymorphic_ctype=regulation_content_type,
    )
    version_group = new_regulation.version_group
    version_group.current_version_id = new_regulation.id
    version_group.save()

    # create the measure type
    new_measure_type_series = MeasureTypeSeries.objects.create(
        id=157,
        sid="C",
        measure_type_combination=MeasureTypeCombination.SINGLE_MEASURE,
        valid_between=date_ranges.no_end,
        update_type=UpdateType.CREATE,
        transaction=transaction,
        version_group=VersionGroup.objects.create(),
        polymorphic_ctype=measure_series_content_type,
    )
    version_group = new_measure_type_series.version_group
    version_group.current_version_id = new_measure_type_series.id
    version_group.save()

    new_measure_type = MeasureType.objects.create(
        sid=142,
        trade_movement_code=ImportExportCode.IMPORT,
        priority_code=1,
        measure_component_applicability_code=ApplicabilityCode.MANDATORY,
        origin_destination_code=ImportExportCode.IMPORT,
        order_number_capture_code=OrderNumberCaptureCode.NOT_PERMITTED,
        measure_explosion_level=MeasureExplosionLevel.HARMONISED_SYSTEM_CHAPTER,
        measure_type_series=new_measure_type_series,
        valid_between=date_ranges.no_end,
        update_type=UpdateType.CREATE,
        transaction=transaction,
        version_group=VersionGroup.objects.create(),
        polymorphic_ctype=measure_type_content_type,
    )
    version_group = new_measure_type.version_group
    version_group.current_version_id = new_measure_type.id
    version_group.save()

    # create the duty expression
    new_duty_expression = DutyExpression.objects.create(
        sid=1,
        duty_amount_applicability_code=ApplicabilityCode.PERMITTED,
        measurement_unit_applicability_code=ApplicabilityCode.PERMITTED,
        monetary_unit_applicability_code=ApplicabilityCode.PERMITTED,
        valid_between=date_ranges.no_end,
        update_type=UpdateType.CREATE,
        transaction=transaction,
        version_group=VersionGroup.objects.create(),
        polymorphic_ctype=duty_expression_content_type,
    )
    version_group = new_duty_expression.version_group
    version_group.current_version_id = new_duty_expression.id
    version_group.save()

    # at this point all the appropriate elements are available within the database for the migration to create the
    # measures and conditions

    # run fix migration
    new_state = migrator.apply_tested_migration(
        ("measures", "0012_add_back_three_missing_measures_already_published"),
    )

    Measure = new_state.apps.get_model("measures", "Measure")

    measures_ids_to_check = [20194965, 20194966, 20194967]

    for measure_id_to_check in measures_ids_to_check:
        # we should be able to get the measures from the database now
        assert Measure.objects.filter(sid=measure_id_to_check).exists() is True
        assert Measure.objects.filter(sid=measure_id_to_check).count() == 1
        measure_to_check = Measure.objects.get(sid=measure_id_to_check)
        # verify the transactions are on the correct partition
        assert measure_to_check.transaction.partition == TransactionPartition.REVISION
        # verify that the current version is as expected
        assert (
            measure_to_check.version_group.current_version_id
            == measure_to_check.trackedmodel_ptr_id
        )

    migrator.reset()


@pytest.mark.django_db()
def test_add_back_deleted_measures_fails_silently_if_data_not_present(
    migrator,
):
    """Ensures that the initial migration works when no data to create measures
    are present, for local dev etc."""

    old_state = migrator.apply_initial_migration(
        (
            "measures",
            "0011_pre_migration_dependencies",
        ),
    )

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
