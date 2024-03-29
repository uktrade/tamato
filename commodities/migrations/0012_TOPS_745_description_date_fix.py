# Generated by Django 3.1.14 on 2022-11-29 11:11

import datetime

from django.db import migrations

from common.validators import UpdateType


def fix_date_on_description(apps, schema_editor):
    """
    Update the validity_start date of the latest approved goods nomenclature
    description for goods nomenclature item id: 2530900010.

    This is a manual change replicating the goods nomenclature description
    period change that takes place in TGB22197 but is missed by the importer
    """
    from common.models.transactions import TransactionPartition

    GoodsNomenclatureDescription = apps.get_model(
        "commodities",
        "GoodsNomenclatureDescription",
    )
    Workbasket = apps.get_model(
        "workbaskets",
        "Workbasket",
    )

    Transaction = apps.get_model(
        "common",
        "Transaction",
    )

    GoodsNomenclature = apps.get_model(
        "commodities",
        "GoodsNomenclature",
    )

    if (
        GoodsNomenclatureDescription.objects.filter(
            trackedmodel_ptr_id=10008934,
        ).exists()
        and Workbasket.objects.filter(id=238).exists()
    ):
        gn_desc_original = GoodsNomenclatureDescription.objects.get(
            trackedmodel_ptr_id=10008934,
        )

        original_workbasket = Workbasket.objects.get(id=238)

        goodsnomenclature_current_version = GoodsNomenclature.objects.get(
            trackedmodel_ptr_id=10008944,
        )

        my_new_transaction = Transaction.objects.create(
            workbasket=original_workbasket,
            order=Transaction.objects.order_by("order").last().order + 1,
            partition=TransactionPartition.REVISION,
            composite_key=str(original_workbasket.id)
            + "-"
            + str(Transaction.objects.order_by("order").last().order + 1)
            + "-"
            + str(TransactionPartition.REVISION),
        )
        new_gn_desc = GoodsNomenclatureDescription.objects.create(
            update_type=UpdateType.UPDATE,
            described_goods_nomenclature_id=goodsnomenclature_current_version.trackedmodel_ptr_id,
            transaction=my_new_transaction,
            description=gn_desc_original.description,
            validity_start=datetime.date(2022, 1, 6),
            version_group=gn_desc_original.version_group,
            polymorphic_ctype_id=gn_desc_original.polymorphic_ctype_id,
        )
        version_group = gn_desc_original.version_group
        version_group.current_version_id = new_gn_desc.trackedmodel_ptr_id
        version_group.save()

    else:
        pass


class Migration(migrations.Migration):
    dependencies = [
        ("commodities", "0011_TOPS_745_migration_dependencies"),
    ]

    operations = [
        migrations.RunPython(fix_date_on_description, migrations.RunPython.noop),
    ]
