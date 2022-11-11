from datetime import date

import pytest

from common.tests import factories
from common.util import TaricDateRange
from common.validators import UpdateType
from measures.models import MeasurementUnit
from workbaskets.tests.util import assert_workbasket_valid


@pytest.mark.django_db()
def test_missing_current_version_fix(migrator):
    """Ensures that the initial migration works."""
    # migrator.apply_initial_migration([("workbaskets", "0005_workbasket_rule_check_task_id"),
    #                                   ("measures", "0010_add_requires_to_action_and_accepts_to_condition_code"),
    #                                   ("common", "0005_transaction_index")])

    # setup
    workbasket = factories.WorkBasketFactory.create()

    with workbasket.new_transaction() as transaction:
        kwargs = {
            "update_type": UpdateType.CREATE,
            "transaction": transaction,
            "valid_between": TaricDateRange(date(2000, 1, 1), None),
            "code": "XXX",
            "description": "made up measurement unit",
            "abbreviation": "xxx",
        }

        measurement_unit = MeasurementUnit.objects.create(**kwargs)

    measurement_unit_id = measurement_unit.trackedmodel_ptr_id

    # publish workbasket
    assert_workbasket_valid(workbasket)
    workbasket.submit_for_approval()
    workbasket.approve()
    workbasket.export_to_cds()
    workbasket.cds_confirmed()

    assert measurement_unit.version_group.current_version_id == measurement_unit_id

    # remove current version from version group
    version_group = measurement_unit.version_group
    version_group.current_version_id = None
    version_group.save()

    # verify setup is correct
    assert measurement_unit.version_group.current_version_id is None
    assert measurement_unit.transaction.partition == 2
    assert measurement_unit.workbasket.status == "PUBLISHED"

    migrator.apply_tested_migration(
        ("common", "0006_auto_20221111_1200_fix_missing_current_versions"),
    )

    measurement_unit = MeasurementUnit.objects.get(
        trackedmodel_ptr_id=measurement_unit_id,
    )

    assert measurement_unit.version_group.current_version_id == measurement_unit_id

    migrator.reset()
