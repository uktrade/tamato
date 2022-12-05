from datetime import date

from django.db import migrations

from common.util import TaricDateRange


def add_back_missing_measures(apps, schemaeditor):
    from commodities.models import GoodsNomenclature
    from common.validators import UpdateType
    from geo_areas.models import GeographicalArea
    from measures.models import DutyExpression
    from measures.models import Measure
    from measures.models import MeasureComponent
    from measures.models import MeasureType
    from regulations.models import Regulation
    from workbaskets.models import WorkBasket

    target_workbasket_id = 545

    # Guard clauses
    if not WorkBasket.objects.filter(id=target_workbasket_id).exists():
        return

    target_work_basket = WorkBasket.objects.get(id=target_workbasket_id)

    if not GeographicalArea.objects.latest_approved().filter(sid=146).exists():
        return

    geographical_area_canada = GeographicalArea.objects.latest_approved().get(
        sid=146,
    )  # Canada

    if (
        not Regulation.objects.latest_approved()
        .filter(regulation_id="C2100006", approved=True)
        .exists()
    ):
        return

    regulation_C2100006 = Regulation.objects.latest_approved().get(
        regulation_id="C2100006",
        approved=True,
    )

    if not MeasureType.objects.filter(sid=142).exists():
        return

    measure_type_tariff_pref = MeasureType.objects.latest_approved().get(sid=142)

    if not DutyExpression.objects.latest_approved().filter(sid=1).exists():
        return

    condition_duty_expression = DutyExpression.objects.latest_approved().get(sid=1)

    if (
        not GoodsNomenclature.objects.latest_approved()
        .filter(item_id="0306920000")
        .exists()
    ):
        return
    if (
        not GoodsNomenclature.objects.latest_approved()
        .filter(item_id="0307190000")
        .exists()
    ):
        return
    if (
        not GoodsNomenclature.objects.latest_approved()
        .filter(item_id="0307490000")
        .exists()
    ):
        return

    transaction = target_work_basket.new_transaction()

    # first measure
    new_measure = Measure.objects.create(
        update_type=UpdateType.CREATE,
        transaction=transaction,
        sid=20194965,
        geographical_area=geographical_area_canada,
        valid_between=TaricDateRange(date(2022, 12, 28), None),
        generating_regulation=regulation_C2100006,
        measure_type=measure_type_tariff_pref,
        goods_nomenclature=GoodsNomenclature.objects.latest_approved().get(
            item_id="0306920000",
        ),
        stopped=False,
    )

    MeasureComponent.objects.create(
        update_type=UpdateType.CREATE,
        transaction=transaction,
        component_measure=new_measure,
        duty_expression=condition_duty_expression,
        duty_amount=0.00,
    )

    transaction = target_work_basket.new_transaction()

    # second measure
    new_measure = Measure.objects.create(
        update_type=UpdateType.CREATE,
        transaction=transaction,
        sid=20194966,
        geographical_area=geographical_area_canada,
        valid_between=TaricDateRange(date(2022, 12, 28), None),
        generating_regulation=regulation_C2100006,
        measure_type=measure_type_tariff_pref,
        goods_nomenclature=GoodsNomenclature.objects.latest_approved().get(
            item_id="0307190000",
        ),
        stopped=False,
    )

    MeasureComponent.objects.create(
        update_type=UpdateType.CREATE,
        transaction=transaction,
        component_measure=new_measure,
        duty_expression=condition_duty_expression,
        duty_amount=0.00,
    )

    transaction = target_work_basket.new_transaction()

    # third measure
    new_measure = Measure.objects.create(
        update_type=UpdateType.CREATE,
        transaction=transaction,
        sid=20194967,
        geographical_area=geographical_area_canada,
        valid_between=TaricDateRange(date(2022, 12, 28), None),
        generating_regulation=regulation_C2100006,
        measure_type=measure_type_tariff_pref,
        goods_nomenclature=GoodsNomenclature.objects.latest_approved().get(
            item_id="0307490000",
        ),
        stopped=False,
    )

    MeasureComponent.objects.create(
        update_type=UpdateType.CREATE,
        transaction=transaction,
        component_measure=new_measure,
        duty_expression=condition_duty_expression,
        duty_amount=0.00,
    )

    target_work_basket.save()


class Migration(migrations.Migration):
    dependencies = [
        ("measures", "0011_pre_migration_dependencies"),
    ]

    operations = [
        migrations.RunPython(
            add_back_missing_measures,
            lambda apps, schema: None,
        ),
    ]
