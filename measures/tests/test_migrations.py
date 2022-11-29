import pytest

from common.tests.factories import ApprovedWorkBasketFactory
from common.tests.factories import DutyExpressionFactory
from common.tests.factories import GeographicalAreaFactory
from common.tests.factories import GoodsNomenclatureFactory
from common.tests.factories import MeasureTypeFactory


@pytest.mark.django_db()
def test_add_back_deleted_measures(migrator):
    migrator.reset()

    """Ensures that the initial migration works."""
    new_state = migrator.apply_initial_migration(
        (
            "measures",
            "0011_pre_migration_dependencies",
        ),
    )

    # setup
    target_workbasket_id = 545

    new_state.apps.get_model("geo_areas", "GeographicalArea")
    new_state.apps.get_model("regulations", "Regulation")
    new_state.apps.get_model("measures", "MeasureType")
    new_state.apps.get_model("commodities", "GoodsNomenclature")
    new_state.apps.get_model("workbaskets", "WorkBasket")
    new_state.apps.get_model("measures", "DutyExpression")
    measurement_class = new_state.apps.get_model("measures", "Measure")

    # mock up workbasket
    new_work_basket = ApprovedWorkBasketFactory.create(id=target_workbasket_id)
    new_work_basket.save()

    new_geographical_area = GeographicalAreaFactory.create(sid=146)
    new_geographical_area.save()
    new_measure_type = MeasureTypeFactory.create(
        regulation_id="C2100006",
        approved=True,
    )
    new_measure_type.save()
    new_duty_expression = DutyExpressionFactory.create(sid=1)
    new_duty_expression.save()
    goods_1 = GoodsNomenclatureFactory.create(item_id="0306920000")
    goods_1.save()
    goods_2 = GoodsNomenclatureFactory.create(item_id="0307190000")
    goods_2.save()
    goods_3 = GoodsNomenclatureFactory.create(item_id="0307490000")
    goods_3.save()

    assert measurement_class.objects.filter(sid=20194965).exists() is False
    assert measurement_class.objects.filter(sid=20194966).exists() is False
    assert measurement_class.objects.filter(sid=20194967).exists() is False

    # run fix migration
    migrator.apply_tested_migration(
        ("measures", "0012_add_back_three_missing_measures_already_published"),
    )

    assert measurement_class.objects.filter(sid=20194965).exists() is True
    assert measurement_class.objects.filter(sid=20194966).exists() is True
    assert measurement_class.objects.filter(sid=20194967).exists() is True

    migrator.reset()
