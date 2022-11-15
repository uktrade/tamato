from datetime import date
from datetime import datetime

import pytest

from common.models.transactions import TransactionPartition
from common.util import TaricDateRange
from common.validators import UpdateType


@pytest.mark.django_db()
def test_missing_current_version_fix(migrator):
    migrator.reset()

    """Ensures that the initial migration works."""
    new_state = migrator.apply_initial_migration(("common", "0006_auto_20221114_1000"))
    # setup

    user_class = new_state.apps.get_model("auth", "User")
    workbasket_class = new_state.apps.get_model("workbaskets", "WorkBasket")
    measurement_unit_class = new_state.apps.get_model("measures", "MeasurementUnit")
    transaction_class = new_state.apps.get_model("common", "Transaction")
    version_group_class = new_state.apps.get_model("common", "VersionGroup")

    # create user
    user = user_class.objects.create(
        email="123123@sdfsdf.com",
        username="sdfsdfsdf",
        first_name="sdfdsf",
        last_name="sdfsdf",
    )
    # Create version group
    version_group = version_group_class.objects.create()
    # create workbasket
    workbasket = workbasket_class.objects.create(
        title=f"xxx {datetime.time}",
        reason="some reason",
        author=user,
    )
    # create transaction
    transaction = transaction_class.objects.create(
        workbasket=workbasket,
        order=1,
        partition=TransactionPartition.REVISION,
    )

    kwargs = {
        "update_type": UpdateType.CREATE,
        "transaction": transaction,
        "valid_between": TaricDateRange(date(2000, 1, 1), None),
        "code": "XXX",
        "description": "made up measurement unit",
        "abbreviation": "xxx",
        "version_group": version_group,
    }

    # create measurement unit
    measurement_unit = measurement_unit_class.objects.create(**kwargs)
    measurement_unit_id = measurement_unit.trackedmodel_ptr_id

    # publish workbasket
    workbasket.status = "PUBLISHED"
    workbasket.save()

    assert measurement_unit.version_group.current_version_id is None

    # run fix migration
    migrator.apply_tested_migration(
        ("common", "0007_auto_20221114_1040_fix_missing_current_versions"),
    )
    measurement_unit = measurement_unit_class.objects.get(
        trackedmodel_ptr_id=measurement_unit_id,
    )

    # assert
    assert measurement_unit.version_group.current_version_id == measurement_unit_id
    migrator.reset()
