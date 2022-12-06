import datetime

import pytest

from common.tests.factories import ApprovedWorkBasketFactory
from common.util import TaricDateRange
from common.validators import UpdateType


@pytest.mark.django_db()
def test_main_migration_works(migrator):
    """Ensures that the description date fix for TOPS-745 migration works."""
    # migrator.reset()

    # before migration
    old_state = migrator.apply_initial_migration(
        ("commodities", "0011_TOPS_745_migration_dependencies"),
    )

    GoodsNomenclatureDescription = old_state.apps.get_model(
        "commodities",
        "GoodsNomenclatureDescription",
    )
    GoodsNomenclature = old_state.apps.get_model("commodities", "GoodsNomenclature")
    Transaction = old_state.apps.get_model("common", "Transaction")
    Workbasket = old_state.apps.get_model("workbaskets", "WorkBasket")
    VersionGroup = old_state.apps.get_model("common", "VersionGroup")

    ApprovedWorkBasketFactory.create().save()
    workbasket = Workbasket.objects.last()
    new_transaction = Transaction.objects.create(
        workbasket=workbasket,
        order=99,
    )

    GoodsNomenclature.objects.create(
        update_type=UpdateType.CREATE,
        transaction=new_transaction,
        version_group=VersionGroup.objects.create(),
        valid_between=TaricDateRange(datetime.date(2020, 1, 6)),
        statistical=False,
    ).save()

    gnd = GoodsNomenclatureDescription.objects.create(
        update_type=UpdateType.CREATE,
        trackedmodel_ptr_id=10008934,
        transaction=new_transaction,
        validity_start=datetime.date(2021, 1, 6),
        described_goods_nomenclature_id=GoodsNomenclature.objects.last().trackedmodel_ptr_id,
        version_group=VersionGroup.objects.create(),
    ).save()

    assert GoodsNomenclatureDescription.objects.get(
        trackedmodel_ptr_id=10008934,
    ).validity_start == datetime.date(2021, 1, 6)

    # after migration
    new_state = migrator.apply_tested_migration(
        ("commodities", "0012_TOPS_745_description_date_fix"),
    )

    GoodsNomenclatureDescription = new_state.apps.get_model(
        "commodities",
        "GoodsNomenclatureDescription",
    )
    assert GoodsNomenclatureDescription.objects.get(
        trackedmodel_ptr_id=10008934,
    ).validity_start == datetime.date(
        2022,
        1,
        6,
    )

    migrator.reset()


@pytest.mark.django_db()
def test_main_migration_ignores_if_no_data(migrator):
    # before migration
    old_state = migrator.apply_initial_migration(
        ("commodities", "0011_TOPS_745_migration_dependencies"),
    )

    GoodsNomenclatureDescription = old_state.apps.get_model(
        "commodities",
        "GoodsNomenclatureDescription",
    )

    assert GoodsNomenclatureDescription.objects.all().count() == 0

    # if this migration works when no data exists, that's a pass
    migrator.apply_tested_migration(
        ("commodities", "0012_TOPS_745_description_date_fix"),
    )

    migrator.reset()
