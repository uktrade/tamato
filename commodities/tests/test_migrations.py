import datetime

import pytest

from common.util import TaricDateRange
from common.validators import UpdateType


@pytest.mark.django_db()
def test_main_migration_works(migrator, setup_content_types):
    """Ensures that the description date fix for TOPS-745 migration works."""

    # before migration
    old_state = migrator.apply_initial_migration(
        ("commodities", "0011_TOPS_745_migration_dependencies"),
    )

    setup_content_types(old_state.apps)

    target_workbasket_id = 238

    GoodsNomenclatureDescription = old_state.apps.get_model(
        "commodities",
        "GoodsNomenclatureDescription",
    )
    GoodsNomenclature = old_state.apps.get_model("commodities", "GoodsNomenclature")
    Transaction = old_state.apps.get_model("common", "Transaction")
    Workbasket = old_state.apps.get_model("workbaskets", "WorkBasket")
    VersionGroup = old_state.apps.get_model("common", "VersionGroup")
    User = old_state.apps.get_model("common", "User")

    user = User.objects.create()
    workbasket = Workbasket.objects.create(id=target_workbasket_id, author=user)
    new_transaction = Transaction.objects.create(
        workbasket=workbasket,
        order=1,
    )

    gn_older_version = GoodsNomenclature.objects.create(
        update_type=UpdateType.CREATE,
        transaction=new_transaction,
        version_group=VersionGroup.objects.create(),
        valid_between=TaricDateRange(datetime.date(2020, 1, 6)),
        statistical=False,
    ).save()

    gn_current_version = GoodsNomenclature.objects.create(
        update_type=UpdateType.CREATE,
        transaction=new_transaction,
        version_group=VersionGroup.objects.create(),
        valid_between=TaricDateRange(datetime.date(2020, 1, 6)),
        statistical=False,
        trackedmodel_ptr_id=10008944,
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
    current_version_id = GoodsNomenclatureDescription.objects.get(
        trackedmodel_ptr_id=10008934,
    ).version_group.current_version_id
    assert GoodsNomenclatureDescription.objects.get(
        trackedmodel_ptr_id=current_version_id,
    ).validity_start == datetime.date(
        2022,
        1,
        6,
    )


@pytest.mark.django_db()
def test_main_migration_ignores_if_no_data(migrator, setup_content_types):
    # before migration
    old_state = migrator.apply_initial_migration(
        ("commodities", "0011_TOPS_745_migration_dependencies"),
    )

    setup_content_types(old_state.apps)

    GoodsNomenclatureDescription = old_state.apps.get_model(
        "commodities",
        "GoodsNomenclatureDescription",
    )

    assert GoodsNomenclatureDescription.objects.all().count() == 0

    # if this migration works when no data exists, that's a pass
    migrator.apply_tested_migration(
        ("commodities", "0012_TOPS_745_description_date_fix"),
    )
