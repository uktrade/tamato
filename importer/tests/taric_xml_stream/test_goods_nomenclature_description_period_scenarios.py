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
        GoodsNomenclatureDescription.objects.filter(
            described_goods_nomenclature__item_id="2903691100",
            described_goods_nomenclature__suffix=80,
        ).count()
        == 1
    )

    taric.process_taric_xml_stream(
        BytesIO(goods_description_with_period_create_xml_as_text.encode()),
        WorkBasketFactory.create().id,
        WorkflowStatus.EDITING,
        get_partition_scheme(settings.TRANSACTION_SCHEMA),
        valid_user.username,
    )

    assert (
        GoodsNomenclatureDescription.objects.filter(
            described_goods_nomenclature__item_id="2903691100",
            described_goods_nomenclature__suffix=80,
        ).count()
        == 2
    )

    assert GoodsNomenclatureDescription.objects.filter(
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
        GoodsNomenclatureDescription.objects.filter(
            described_goods_nomenclature__item_id="2903691100",
            described_goods_nomenclature__suffix=80,
        ).count()
        == 1
    )

    taric.process_taric_xml_stream(
        BytesIO(goods_description_with_period_create_period_first_xml_as_text.encode()),
        WorkBasketFactory.create().id,
        WorkflowStatus.EDITING,
        get_partition_scheme(settings.TRANSACTION_SCHEMA),
        valid_user.username,
    )

    assert (
        GoodsNomenclatureDescription.objects.filter(
            described_goods_nomenclature__item_id="2903691100",
            described_goods_nomenclature__suffix=80,
        ).count()
        == 2
    )

    assert GoodsNomenclatureDescription.objects.filter(
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
    """This test simulates an uncommon but valid update from the EU where a
    description links to a previously defined period."""
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        },
    }

    assert (
        GoodsNomenclatureDescription.objects.filter(
            described_goods_nomenclature__item_id="2903691100",
            described_goods_nomenclature__suffix=80,
        ).count()
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
        GoodsNomenclatureDescription.objects.filter(
            described_goods_nomenclature__item_id="2903691100",
            described_goods_nomenclature__suffix=80,
        ).count()
    ) == 2

    assert (
        GoodsNomenclatureDescription.objects.filter(
            described_goods_nomenclature__item_id="2903691100",
            described_goods_nomenclature__suffix=80,
        )
        .order_by("trackedmodel_ptr_id")
        .last()
        .validity_start
        == date.today()
    )
