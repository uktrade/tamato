from datetime import date

from django.db import migrations

from common.util import TaricDateRange


def add_back_missing_measures(apps, schemaeditor):
    target_workbasket_id = 545
    measure = apps.get_model("measures", "Measure")
    measure_component = apps.get_model("measures", "MeasureComponent")
    apps.get_model("measures", "MeasureCondition")
    geographical_area = apps.get_model("geo_areas", "GeographicalArea")
    regulation = apps.get_model("regulations", "Regulation")
    measure_type = apps.get_model("measures", "MeasureType")
    goods_nomenclature = apps.get_model("commodities", "GoodsNomenclature")
    work_basket = apps.get_model("workbaskets", "WorkBasket")
    duty_expression = apps.get_model("measures", "DutyExpression")

    # Guard clauseS
    if not work_basket.objects.filter(id=target_workbasket_id).exists():
        return

    target_work_basket = work_basket.objects.get(id=target_workbasket_id)

    if not geographical_area.objects.filter(sid=146).exists():
        return

    geographical_area_canada = geographical_area.objects.get(sid=146)  # Canada

    if (
        not regulation.objects.latest_approved()
        .filter(regulation_id="C2100006", approved=True)
        .exists()
    ):
        return

    regulation_C2100006 = regulation.objects.get(
        regulation_id="C2100006",
        approved=True,
    )

    if not measure_type.objects.latest_approved().filter(sid=142).exists():
        return

    measure_type_tariff_pref = measure_type.objects.latest_approved().get(sid=142)

    if not duty_expression.objects.latest_approved().filter(sid=1).exists():
        return

    condition_duty_expression = duty_expression.objects.latest_approved().get(sid=1)

    if (
        not goods_nomenclature.objects.latest_approved()
        .filter(item_id="0306920000")
        .exists()
    ):
        return
    if (
        not goods_nomenclature.objects.latest_approved()
        .filter(item_id="0307190000")
        .exists()
    ):
        return
    if (
        not goods_nomenclature.objects.latest_approved()
        .filter(item_id="0307490000")
        .exists()
    ):
        return

    transaction = target_work_basket.new_transaction()

    # first measure
    new_measure = measure.objects.create(
        transaction=transaction,
        sid=20194965,
        geographical_area=geographical_area_canada,
        valid_between=TaricDateRange(date(2022, 12, 28), None),
        generating_regulation=regulation_C2100006,
        measure_type=measure_type_tariff_pref,
        goods_nomenclature=goods_nomenclature.objects.latest_approved().get(
            item_id="0306920000",
        ),
        stopped=False,
    )

    measure_component.objects.create(
        transaction=transaction,
        measure=new_measure,
        duty_expression=condition_duty_expression,
        duty_ammount=0.00,
    )

    transaction = target_work_basket.new_transaction()

    # second measure
    new_measure = measure.objects.create(
        transaction=transaction,
        sid=20194966,
        geographical_area=geographical_area_canada,
        valid_between=TaricDateRange(date(2022, 12, 28), None),
        generating_regulation=regulation_C2100006,
        measure_type=measure_type_tariff_pref,
        goods_nomenclature=goods_nomenclature.objects.latest_approved().get(
            item_id="0307190000",
        ),
        stopped=False,
    )

    measure_component.objects.create(
        transaction=transaction,
        measure=new_measure,
        duty_expression=condition_duty_expression,
        duty_ammount=0.00,
    )

    transaction = target_work_basket.new_transaction()

    # third measure
    new_measure = measure.objects.create(
        transaction=transaction,
        sid=20194967,
        geographical_area=geographical_area_canada,
        valid_between=TaricDateRange(date(2022, 12, 28), None),
        generating_regulation=regulation_C2100006,
        measure_type=measure_type_tariff_pref,
        goods_nomenclature=goods_nomenclature.objects.latest_approved().get(
            item_id="0307490000",
        ),
        stopped=False,
    )

    measure_component.objects.create(
        transaction=transaction,
        measure=new_measure,
        duty_expression=condition_duty_expression,
        duty_ammount=0.00,
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
