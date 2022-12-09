from io import BytesIO

import pytest

import settings
from commodities.models import GoodsNomenclature
from commodities.models import GoodsNomenclatureDescription
from common.models.transactions import Transaction
from common.tests.factories import ApprovedWorkBasketFactory
from common.tests.factories import GoodsNomenclatureDescriptionFactory
from common.tests.factories import GoodsNomenclatureFactory
from importer import taric
from workbaskets.models import get_partition_scheme
from workbaskets.validators import WorkflowStatus

pytestmark = pytest.mark.django_db


def test_process_taric_xml_stream_correctly_imports_text_only_changes_to_comm_code_descriptions(
    goods_description_only_update_xml_as_text,
    valid_user,
    chunk,
    object_nursery,
):
    # create seed data for test
    # <oub:goods.nomenclature.description.period.sid>143415
    # </oub:goods.nomenclature.description.period.sid>
    # <oub:language.id>EN</oub:language.id>
    # <oub:goods.nomenclature.sid>103510</oub:goods.nomenclature.sid>
    # <oub:goods.nomenclature.item.id>0306129091</oub:goods.nomenclature.item.id>
    # <oub:productline.suffix>80</oub:productline.suffix>
    # <oub:description>Cooked, in shell</oub:description>

    # workbasket from factory
    workbasket = ApprovedWorkBasketFactory.create()

    # Create goods nomenclature & description
    GoodsNomenclatureFactory.create(sid=103510, item_id="0306129091", suffix=80).save(
        force_write=True,
    )
    GoodsNomenclatureDescriptionFactory.create(
        sid=143415,
        described_goods_nomenclature=GoodsNomenclature.objects.get(sid=103510),
        description="some description",
    ).save(force_write=True)

    goods_nomenclature_description = (
        GoodsNomenclatureDescription.objects.latest_approved().get(sid=143415)
    )

    assert goods_nomenclature_description.description == "some description"
    assert GoodsNomenclatureDescription.objects.count() == 1

    # mock taric stream with a measure with end date
    xml_text = goods_description_only_update_xml_as_text

    taric.process_taric_xml_stream(
        BytesIO(xml_text.encode()),
        workbasket.id,
        WorkflowStatus.EDITING,
        get_partition_scheme(settings.TRANSACTION_SCHEMA),
        valid_user.username,
    )

    # verify the changes are in the latest transaction
    latest_transaction = Transaction.objects.last()

    updated_goods_nomenclature_description = (
        GoodsNomenclatureDescription.objects.approved_up_to_transaction(
            latest_transaction,
        ).get(sid=143415)
    )

    assert GoodsNomenclatureDescription.objects.count() == 2
    assert updated_goods_nomenclature_description.description == "A new description"
