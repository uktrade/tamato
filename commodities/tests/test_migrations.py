import datetime
import pytest

import conftest
from common.tests.factories import GoodsNomenclatureDescriptionFactory


@pytest.mark.django_db()
def test_main_migration0011(migrator):
    """Ensures that the description date fix for TOPS-745 migration works."""
    # migrator.reset()

    # before migration
    old_state = migrator.apply_initial_migration(
        ('commodities', '0010_delete_goodsnomenclatureindentnode'))

    conftest.setup_content_types(old_state.apps)

    GoodsNomenclatureDescription = old_state.apps.get_model('commodities',
                                                            'GoodsNomenclatureDescription')

    gn_description = GoodsNomenclatureDescriptionFactory.create(
        trackedmodel_ptr_id=10008934,
        validity_start=datetime.date(2021, 1, 6)
    )

    assert GoodsNomenclatureDescription.objects.get(
        trackedmodel_ptr_id=10008934).validity_start == datetime.date(2021, 1,
                                                                      6)

    # after migration
    new_state = migrator.before(
        ('commodities', '0011_description_date_fix_for_TOPS_745'))
    GoodsNomenclatureDescription = new_state.apps.get_model('commodities',
                                                            'GoodsNomenclatureDescription')
    assert GoodsNomenclatureDescription.objects.get(
        trackedmodel_ptr_id=10008934).validity_start == datetime.date(2022, 1,
                                                                      6)
