from datetime import date
from io import BytesIO

import pytest

from commodities.models import GoodsNomenclatureDescription
from common.tests import factories
from common.tests.factories import WorkBasketFactory
from importer import taric
from workbaskets.models import get_partition_scheme
from workbaskets.validators import WorkflowStatus

pytestmark = pytest.mark.django_db


# Test import works with order period then description

# test importer works with order description then period

#
# class TestTaric:
#     def test_process_taric_xml_stream_correctly_imports_text_only_changes_to_comm_code_descriptions(
#             self,
#             goods_description_only_update_xml_as_text,
#             valid_user,
#             chunk,
#             object_nursery,
#             settings,
#     ):
#         # workbasket from factory
#         workbasket = QueuedWorkBasketFactory.create()
#
#         # Create goods nomenclature & description
#         GoodsNomenclatureFactory.create(
#             sid=103510,
#             item_id="0306129091",
#             suffix=80,
#             description__sid=143415,
#             description__description="some description",
#         ).save(force_write=True)
#
#         goods_nomenclature_description = (
#             GoodsNomenclatureDescription.objects.latest_approved().get(sid=143415)
#         )
#
#         assert goods_nomenclature_description.description == "some description"
#         assert GoodsNomenclatureDescription.objects.count() == 1
#
#         # mock taric stream with a measure with end date
#         xml_text = goods_description_only_update_xml_as_text
#
#         print("before xml processing")
#
#         settings.CACHES = {
#             "default": {
#                 "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
#             },
#         }
#
#         taric.process_taric_xml_stream(
#             BytesIO(xml_text.encode()),
#             workbasket.id,
#             WorkflowStatus.EDITING,
#             get_partition_scheme(settings.TRANSACTION_SCHEMA),
#             valid_user.username,
#         )
#
#         # verify the changes are in the latest transaction
#         latest_transaction = Transaction.objects.last()
#
#         updated_goods_nomenclature_description = (
#             GoodsNomenclatureDescription.objects.approved_up_to_transaction(
#                 latest_transaction,
#             ).get(sid=143415)
#         )
#
#         assert (
#                 GoodsNomenclatureDescription.objects.all().filter(sid=143415).count() == 2
#         )
#         assert updated_goods_nomenclature_description.description == "A new description"
#
#     def test_process_taric_xml_stream_correctly_imports_comm_code_with_period(
#             self,
#             goods_description_with_period_create_xml_as_text,
#             valid_user,
#             chunk,
#             object_nursery,
#             settings,
#     ):
#         assert GoodsNomenclature.objects.all().filter(sid=54321).count() == 0
#
#         # mock taric stream with a measure with end date
#         xml_text = goods_description_with_period_create_xml_as_text
#
#         print("before xml processing")
#
#         settings.CACHES = {
#             "default": {
#                 "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
#             },
#         }
#
#         # workbasket from factory
#         workbasket = QueuedWorkBasketFactory.create()
#
#         taric.process_taric_xml_stream(
#             BytesIO(xml_text.encode()),
#             workbasket.id,
#             WorkflowStatus.EDITING,
#             get_partition_scheme(settings.TRANSACTION_SCHEMA),
#             valid_user.username,
#         )
#
#         print("after xml processing")
#
#         assert GoodsNomenclature.objects.all().filter(sid=54321).count() == 1
#
#
#
#
# def test_process_taric_xml_stream_correctly_imports_text_only_changes_to_comm_code_descriptions(
#         goods_description_only_update_xml_as_text,
#         valid_user,
#         chunk,
#         object_nursery,
# ):
#     # create seed data for test
#     # <oub:goods.nomenclature.description.period.sid>143415
#     # </oub:goods.nomenclature.description.period.sid>
#     # <oub:language.id>EN</oub:language.id>
#     # <oub:goods.nomenclature.sid>103510</oub:goods.nomenclature.sid>
#     # <oub:goods.nomenclature.item.id>0306129091</oub:goods.nomenclature.item.id>
#     # <oub:productline.suffix>80</oub:productline.suffix>
#     # <oub:description>Cooked, in shell</oub:description>
#
#     # workbasket from factory
#     workbasket = PublishedWorkBasketFactory.create()
#
#     # Create goods nomenclature & description
#     GoodsNomenclatureFactory.create(
#         sid=103510,
#         item_id="0306129091",
#         suffix=80,
#         description__sid=143415,
#         description__description="some description",
#     ).save(force_write=True)
#
#     goods_nomenclature_description = (
#         GoodsNomenclatureDescription.objects.latest_approved().get(sid=143415)
#     )
#
#     assert goods_nomenclature_description.description == "some description"
#     assert GoodsNomenclatureDescription.objects.count() == 1
#
#     # mock taric stream with a measure with end date
#     xml_text = goods_description_only_update_xml_as_text
#
#     taric.process_taric_xml_stream(
#         BytesIO(xml_text.encode()),
#         workbasket.id,
#         WorkflowStatus.EDITING,
#         get_partition_scheme(settings.TRANSACTION_SCHEMA),
#         valid_user.username,
#     )
#
#     # verify the changes are in the latest transaction
#     latest_transaction = Transaction.objects.last()
#
#     updated_goods_nomenclature_description = (
#         GoodsNomenclatureDescription.objects.approved_up_to_transaction(
#             latest_transaction,
#         ).get(sid=143415)
#     )
#
#     assert GoodsNomenclatureDescription.objects.count() == 2
#     assert updated_goods_nomenclature_description.description == "A new description"
#
#
# def test_process_taric_xml_stream_correctly_adds_comm_code_description_periods_to_nursery(
#         goods_description_only_update_xml_as_text,
#         valid_user,
#         chunk,
#         object_nursery,
# ):
#     # create seed data for test
#     # <oub:goods.nomenclature.description.period.sid>143415
#     # </oub:goods.nomenclature.description.period.sid>
#     # <oub:language.id>EN</oub:language.id>
#     # <oub:goods.nomenclature.sid>103510</oub:goods.nomenclature.sid>
#     # <oub:goods.nomenclature.item.id>0306129091</oub:goods.nomenclature.item.id>
#     # <oub:productline.suffix>80</oub:productline.suffix>
#     # <oub:description>Cooked, in shell</oub:description>
#
#     # workbasket from factory
#     workbasket = PublishedWorkBasketFactory.create()
#
#     # Create goods nomenclature & description
#     GoodsNomenclatureFactory.create(
#         sid=103510,
#         item_id="0306129091",
#         suffix=80,
#         description__sid=143415,
#         description__description="some description",
#     ).save(force_write=True)
#
#     goods_nomenclature_description = (
#         GoodsNomenclatureDescription.objects.latest_approved().get(sid=143415)
#     )
#
#     assert goods_nomenclature_description.description == "some description"
#     assert GoodsNomenclatureDescription.objects.count() == 1
#
#     # mock taric stream with a measure with end date
#     xml_text = goods_description_only_update_xml_as_text
#
#
#     with mock.patch("common.tariffs_api.get_quota_definitions_data", ) as mock_get_quotas:
#
#         taric.process_taric_xml_stream(
#             BytesIO(xml_text.encode()),
#             workbasket.id,
#             WorkflowStatus.EDITING,
#             get_partition_scheme(settings.TRANSACTION_SCHEMA),
#             valid_user.username,
#         )
#
#     # verify the changes are in the latest transaction
#     latest_transaction = Transaction.objects.last()
#
#     updated_goods_nomenclature_description = (
#         GoodsNomenclatureDescription.objects.approved_up_to_transaction(
#             latest_transaction,
#         ).get(sid=143415)
#     )
#
#     assert GoodsNomenclatureDescription.objects.count() == 2
#     assert updated_goods_nomenclature_description.description == "A new description"
#
#
# def test_process_taric_xml_stream_correctly_imports_text_only_changes_to_comm_code_descriptions(
#         goods_description_only_update_xml_as_text,
#         valid_user,
#         chunk,
#         object_nursery,
# ):
#     # create seed data for test
#     # <oub:goods.nomenclature.description.period.sid>143415
#     # </oub:goods.nomenclature.description.period.sid>
#     # <oub:language.id>EN</oub:language.id>
#     # <oub:goods.nomenclature.sid>103510</oub:goods.nomenclature.sid>
#     # <oub:goods.nomenclature.item.id>0306129091</oub:goods.nomenclature.item.id>
#     # <oub:productline.suffix>80</oub:productline.suffix>
#     # <oub:description>Cooked, in shell</oub:description>
#
#     # workbasket from factory
#     workbasket = PublishedWorkBasketFactory.create()
#
#     # Create goods nomenclature & description
#     GoodsNomenclatureFactory.create(
#         sid=103510,
#         item_id="0306129091",
#         suffix=80,
#         description__sid=143415,
#         description__description="some description",
#     ).save(force_write=True)
#
#     goods_nomenclature_description = (
#         GoodsNomenclatureDescription.objects.latest_approved().get(sid=143415)
#     )
#
#     assert goods_nomenclature_description.description == "some description"
#     assert GoodsNomenclatureDescription.objects.count() == 1
#
#     # mock taric stream with a measure with end date
#     xml_text = goods_description_only_update_xml_as_text
#
#     taric.process_taric_xml_stream(
#         BytesIO(xml_text.encode()),
#         workbasket.id,
#         WorkflowStatus.EDITING,
#         get_partition_scheme(settings.TRANSACTION_SCHEMA),
#         valid_user.username,
#     )
#
#     # verify the changes are in the latest transaction
#     latest_transaction = Transaction.objects.last()
#
#     updated_goods_nomenclature_description = (
#         GoodsNomenclatureDescription.objects.approved_up_to_transaction(
#             latest_transaction,
#         ).get(sid=143415)
#     )
#
#     assert GoodsNomenclatureDescription.objects.count() == 2
#     assert updated_goods_nomenclature_description.description == "A new description"
#
#
# def test_process_taric_xml_stream_reports_on_missing_dependencies(
#         goods_description_only_update_xml_as_text,
#         valid_user,
#         chunk,
#         object_nursery,
# ):
#     # workbasket from factory
#     workbasket = PublishedWorkBasketFactory.create()
#
#     # Create goods nomenclature & description
#     GoodsNomenclatureFactory.create(
#         sid=103510,
#         item_id="0306129091",
#         suffix=80,
#         description__sid=143415,
#         description__description="some description",
#     ).save(force_write=True)
#
#     goods_nomenclature_description = (
#         GoodsNomenclatureDescription.objects.latest_approved().get(sid=143415)
#     )
#
#     assert goods_nomenclature_description.description == "some description"
#     assert GoodsNomenclatureDescription.objects.count() == 1
#
#     # mock taric stream with a measure with end date
#     xml_text = goods_description_only_update_xml_as_text
#
#     with mock.patch("common.tariffs_api.get_quota_definitions_data", ) as mock_get_quotas:
#
#         taric.process_taric_xml_stream(
#             BytesIO(xml_text.encode()),
#             workbasket.id,
#             WorkflowStatus.EDITING,
#             get_partition_scheme(settings.TRANSACTION_SCHEMA),
#             valid_user.username,
#         )
#
#     # verify the changes are in the latest transaction
#     latest_transaction = Transaction.objects.last()
#
#     updated_goods_nomenclature_description = (
#         GoodsNomenclatureDescription.objects.approved_up_to_transaction(
#             latest_transaction,
#         ).get(sid=143415)
#     )
#
#     assert GoodsNomenclatureDescription.objects.count() == 2
#     assert updated_goods_nomenclature_description.description == "A new description"


@pytest.fixture()
def seed_database_with_indented_goods():
    factories.TransactionFactory.create()

    factories.GoodsNomenclatureFactory.create(
        item_id="2903000000",
        suffix=10,
        indent__indent=0,
    )

    factories.GoodsNomenclatureFactory.create(
        item_id="2903000000",
        suffix=10,
        indent__indent=1,
    )

    factories.GoodsNomenclatureFactory.create(
        item_id="2903690000",
        suffix=10,
        indent__indent=2,
    )

    factories.GoodsNomenclatureFactory.create(
        item_id="2903691100",
        suffix=10,
        indent__indent=3,
    )

    factories.GoodsNomenclatureFactory.create(
        item_id="2903691100",
        sid=54321,
        suffix=80,
        indent__indent=4,
    )


def test_correctly_imports_comm_code_description_with_period_after(
    seed_database_with_indented_goods,
    goods_description_with_period_create_xml_as_text,
    valid_user,
    chunk,
    object_nursery,
    settings,
):
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        },
    }

    assert (
        GoodsNomenclatureDescription.objects.all()
        .filter(
            described_goods_nomenclature__item_id="2903691100",
            described_goods_nomenclature__suffix=80,
        )
        .count()
        == 1
    )

    taric.process_taric_xml_stream(
        BytesIO(goods_description_with_period_create_xml_as_text.encode()),
        WorkBasketFactory.create().id,
        WorkflowStatus.EDITING,
        get_partition_scheme(settings.TRANSACTION_SCHEMA),
        valid_user.username,
    )

    print("after xml processing")

    assert (
        GoodsNomenclatureDescription.objects.all()
        .filter(
            described_goods_nomenclature__item_id="2903691100",
            described_goods_nomenclature__suffix=80,
        )
        .count()
        == 2
    )

    assert GoodsNomenclatureDescription.objects.all().filter(
        described_goods_nomenclature__item_id="2903691100",
        described_goods_nomenclature__suffix=80,
    ).order_by("trackedmodel_ptr_id").last().validity_start == date(2022, 5, 13)


def test_correctly_imports_comm_code_description_with_period_before(
    seed_database_with_indented_goods,
    goods_description_with_period_create_period_first_xml_as_text,
    valid_user,
    chunk,
    object_nursery,
    settings,
):
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        },
    }

    assert (
        GoodsNomenclatureDescription.objects.all()
        .filter(
            described_goods_nomenclature__item_id="2903691100",
            described_goods_nomenclature__suffix=80,
        )
        .count()
        == 1
    )

    taric.process_taric_xml_stream(
        BytesIO(goods_description_with_period_create_period_first_xml_as_text.encode()),
        WorkBasketFactory.create().id,
        WorkflowStatus.EDITING,
        get_partition_scheme(settings.TRANSACTION_SCHEMA),
        valid_user.username,
    )

    print("after xml processing")

    assert (
        GoodsNomenclatureDescription.objects.all()
        .filter(
            described_goods_nomenclature__item_id="2903691100",
            described_goods_nomenclature__suffix=80,
        )
        .count()
        == 2
    )

    assert GoodsNomenclatureDescription.objects.all().filter(
        described_goods_nomenclature__item_id="2903691100",
        described_goods_nomenclature__suffix=80,
    ).order_by("trackedmodel_ptr_id").last().validity_start == date(2022, 5, 13)


def test_correctly_imports_comm_code_description_with_no_period(
    seed_database_with_indented_goods,
    goods_description_only_create_xml_as_text,
    valid_user,
    chunk,
    object_nursery,
    settings,
):
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        },
    }

    assert (
        GoodsNomenclatureDescription.objects.all()
        .filter(
            described_goods_nomenclature__item_id="2903691100",
            described_goods_nomenclature__suffix=80,
        )
        .count()
        == 1
    )

    taric.process_taric_xml_stream(
        BytesIO(goods_description_only_create_xml_as_text.encode()),
        WorkBasketFactory.create().id,
        WorkflowStatus.EDITING,
        get_partition_scheme(settings.TRANSACTION_SCHEMA),
        valid_user.username,
    )

    assert (
        GoodsNomenclatureDescription.objects.all()
        .filter(
            described_goods_nomenclature__item_id="2903691100",
            described_goods_nomenclature__suffix=80,
        )
        .count()
    ) == 2

    assert GoodsNomenclatureDescription.objects.all().filter(
        described_goods_nomenclature__item_id="2903691100",
        described_goods_nomenclature__suffix=80,
    ).order_by("trackedmodel_ptr_id").last().validity_start == date(2022, 5, 13)
