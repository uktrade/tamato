from datetime import date

from django.db import migrations

from common.util import TaricDateRange


def add_back_missing_measures(apps, schemaeditor):
    target_workbasket_id = 545
    measure = apps.get_model("measures", "Measure")
    apps.get_model("measures", "MeasureCondition")
    geographical_area = apps.get_model("geo_areas", "GeographicalArea")
    regulation = apps.get_model("measures", "Regulation")
    measure_type = apps.get_model("measures", "MeasureType")
    goods_nomenclature = apps.get_model("commodities", "GoodsNomenclature")
    work_basket = apps.get_model("work_basket", "WorkBasket")

    target_work_basket = work_basket.objects.get(id=target_workbasket_id)
    geographical_area_canada = geographical_area.objects.latest_approved().get(
        description__description="Canada",
    )
    regulation_C2100006 = regulation.objects.latest_approved().get(
        regulation_id="C2100006",
    )
    measure_type_tariff_pref = measure_type.objects.latest_approved().get(sid=142)

    # XML send to CDS
    #       <env:transaction id="462550">
    #         <env:app.message id="625">
    #             <oub:transmission xmlns:oub="urn:publicid:-:DGTAXUD:TARIC:MESSAGE:1.0"
    #                               xmlns:env="urn:publicid:-:DGTAXUD:GENERAL:ENVELOPE:1.0">
    #                 <oub:record>
    #                     <oub:transaction.id>462550</oub:transaction.id>
    #                     <oub:record.code>430</oub:record.code>
    #                     <oub:subrecord.code>00</oub:subrecord.code>
    #                     <oub:record.sequence.number>1</oub:record.sequence.number>
    #                     <oub:update.type>3</oub:update.type>
    #                     <oub:measure>
    #                         <oub:measure.sid>20194965</oub:measure.sid>
    #                         <oub:measure.type>142</oub:measure.type>
    #                         <oub:geographical.area>CA</oub:geographical.area>
    #                         <oub:goods.nomenclature.item.id>0306920000</oub:goods.nomenclature.item.id>
    #                         <oub:validity.start.date>2021-12-28</oub:validity.start.date>
    #                         <oub:measure.generating.regulation.role>1</oub:measure.generating.regulation.role>
    #                         <oub:measure.generating.regulation.id>C2100006</oub:measure.generating.regulation.id>
    #                         <oub:stopped.flag>0</oub:stopped.flag>
    #                         <oub:geographical.area.sid>146</oub:geographical.area.sid>
    #                         <oub:goods.nomenclature.sid>100743</oub:goods.nomenclature.sid>
    #                     </oub:measure>
    #                 </oub:record>
    #             </oub:transmission>
    #         </env:app.message>
    #         <env:app.message id="626">
    #             <oub:transmission xmlns:oub="urn:publicid:-:DGTAXUD:TARIC:MESSAGE:1.0"
    #                               xmlns:env="urn:publicid:-:DGTAXUD:GENERAL:ENVELOPE:1.0">
    #                 <oub:record>
    #                     <oub:transaction.id>462550</oub:transaction.id>
    #                     <oub:record.code>430</oub:record.code>
    #                     <oub:subrecord.code>05</oub:subrecord.code>
    #                     <oub:record.sequence.number>1</oub:record.sequence.number>
    #                     <oub:update.type>3</oub:update.type>
    #                     <oub:measure.component>
    #                         <oub:measure.sid>20194965</oub:measure.sid>
    #                         <oub:duty.expression.id>01</oub:duty.expression.id>
    #                         <oub:duty.amount>0.000</oub:duty.amount>
    #                     </oub:measure.component>
    #                 </oub:record>
    #             </oub:transmission>
    #         </env:app.message>
    #     </env:transaction>

    transaction = target_work_basket.new_transaction()

    # first measure
    measure.objects.create(
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

    # XML send to CDS
    #    <env:transaction id="462551">
    #         <env:app.message id="627">
    #             <oub:transmission xmlns:oub="urn:publicid:-:DGTAXUD:TARIC:MESSAGE:1.0"
    #                               xmlns:env="urn:publicid:-:DGTAXUD:GENERAL:ENVELOPE:1.0">
    #                 <oub:record>
    #                     <oub:transaction.id>462551</oub:transaction.id>
    #                     <oub:record.code>430</oub:record.code>
    #                     <oub:subrecord.code>00</oub:subrecord.code>
    #                     <oub:record.sequence.number>1</oub:record.sequence.number>
    #                     <oub:update.type>3</oub:update.type>
    #                     <oub:measure>
    #                         <oub:measure.sid>20194966</oub:measure.sid>
    #                         <oub:measure.type>142</oub:measure.type>
    #                         <oub:geographical.area>CA</oub:geographical.area>
    #                         <oub:goods.nomenclature.item.id>0307190000</oub:goods.nomenclature.item.id>
    #                         <oub:validity.start.date>2021-12-28</oub:validity.start.date>
    #                         <oub:measure.generating.regulation.role>1</oub:measure.generating.regulation.role>
    #                         <oub:measure.generating.regulation.id>C2100006</oub:measure.generating.regulation.id>
    #                         <oub:stopped.flag>0</oub:stopped.flag>
    #                         <oub:geographical.area.sid>146</oub:geographical.area.sid>
    #                         <oub:goods.nomenclature.sid>95308</oub:goods.nomenclature.sid>
    #                     </oub:measure>
    #                 </oub:record>
    #             </oub:transmission>
    #         </env:app.message>
    #         <env:app.message id="628">
    #             <oub:transmission xmlns:oub="urn:publicid:-:DGTAXUD:TARIC:MESSAGE:1.0"
    #                               xmlns:env="urn:publicid:-:DGTAXUD:GENERAL:ENVELOPE:1.0">
    #                 <oub:record>
    #                     <oub:transaction.id>462551</oub:transaction.id>
    #                     <oub:record.code>430</oub:record.code>
    #                     <oub:subrecord.code>05</oub:subrecord.code>
    #                     <oub:record.sequence.number>1</oub:record.sequence.number>
    #                     <oub:update.type>3</oub:update.type>
    #                     <oub:measure.component>
    #                         <oub:measure.sid>20194966</oub:measure.sid>
    #                         <oub:duty.expression.id>01</oub:duty.expression.id>
    #                         <oub:duty.amount>0.000</oub:duty.amount>
    #                     </oub:measure.component>
    #                 </oub:record>
    #             </oub:transmission>
    #         </env:app.message>
    #     </env:transaction>

    transaction = target_work_basket.new_transaction()

    # second measure
    measure.objects.create(
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

    # XML send to CDS
    #    <env:transaction id="462552">
    #         <env:app.message id="629">
    #             <oub:transmission xmlns:oub="urn:publicid:-:DGTAXUD:TARIC:MESSAGE:1.0"
    #                               xmlns:env="urn:publicid:-:DGTAXUD:GENERAL:ENVELOPE:1.0">
    #                 <oub:record>
    #                     <oub:transaction.id>462552</oub:transaction.id>
    #                     <oub:record.code>430</oub:record.code>
    #                     <oub:subrecord.code>00</oub:subrecord.code>
    #                     <oub:record.sequence.number>1</oub:record.sequence.number>
    #                     <oub:update.type>3</oub:update.type>
    #                     <oub:measure>
    #                         <oub:measure.sid>20194967</oub:measure.sid>
    #                         <oub:measure.type>142</oub:measure.type>
    #                         <oub:geographical.area>CA</oub:geographical.area>
    #                         <oub:goods.nomenclature.item.id>0307490000</oub:goods.nomenclature.item.id>
    #                         <oub:validity.start.date>2021-12-28</oub:validity.start.date>
    #                         <oub:measure.generating.regulation.role>1</oub:measure.generating.regulation.role>
    #                         <oub:measure.generating.regulation.id>C2100006</oub:measure.generating.regulation.id>
    #                         <oub:stopped.flag>0</oub:stopped.flag>
    #                         <oub:geographical.area.sid>146</oub:geographical.area.sid>
    #                         <oub:goods.nomenclature.sid>29355</oub:goods.nomenclature.sid>
    #                     </oub:measure>
    #                 </oub:record>
    #             </oub:transmission>
    #         </env:app.message>
    #         <env:app.message id="630">
    #             <oub:transmission xmlns:oub="urn:publicid:-:DGTAXUD:TARIC:MESSAGE:1.0"
    #                               xmlns:env="urn:publicid:-:DGTAXUD:GENERAL:ENVELOPE:1.0">
    #                 <oub:record>
    #                     <oub:transaction.id>462552</oub:transaction.id>
    #                     <oub:record.code>430</oub:record.code>
    #                     <oub:subrecord.code>05</oub:subrecord.code>
    #                     <oub:record.sequence.number>1</oub:record.sequence.number>
    #                     <oub:update.type>3</oub:update.type>
    #                     <oub:measure.component>
    #                         <oub:measure.sid>20194967</oub:measure.sid>
    #                         <oub:duty.expression.id>01</oub:duty.expression.id>
    #                         <oub:duty.amount>0.000</oub:duty.amount>
    #                     </oub:measure.component>
    #                 </oub:record>
    #             </oub:transmission>
    #         </env:app.message>
    #     </env:transaction>

    transaction = target_work_basket.new_transaction()

    # third measure
    measure.objects.create(
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


class Migration(migrations.Migration):
    dependencies = [
        ("measures", "0010_add_requires_to_action_and_accepts_to_condition_code"),
    ]

    operations = [
        migrations.RunPython(
            add_back_missing_measures,
            lambda apps, schema: None,
        ),
    ]
