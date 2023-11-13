import os
import shutil
from pathlib import Path
from typing import Sequence
from typing import Type

import pytest
from django.forms.models import model_to_dict
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from common.serializers import TrackedModelSerializerMixin
from common.serializers import ValiditySerializerMixin
from common.tests import factories
from common.tests.models import TestModel1
from common.tests.util import generate_test_import_xml
from importer.handlers import BaseHandler
from importer.namespaces import TARIC_RECORD_GROUPS
from importer.namespaces import Tag
from importer.namespaces import TTags
from importer.namespaces import make_schema_dataclass
from importer.namespaces import xsd_schema_paths
from importer.nursery import TariffObjectNursery
from importer.nursery import get_nursery


def get_project_root():
    return Path(__file__).parents[2]


@pytest.fixture
def object_nursery() -> TariffObjectNursery:
    nursery = get_nursery()
    yield nursery
    nursery.cache.clear()


@pytest.fixture
def mock_serializer() -> Type[ModelSerializer]:
    class TestSerializer(TrackedModelSerializerMixin, ValiditySerializerMixin):
        sid = serializers.IntegerField()

        class Meta:
            model = TestModel1
            exclude = ("version_group",)

    return TestSerializer


@pytest.fixture
def parser_class(mock_serializer) -> Type[BaseHandler]:
    class TestHandler(BaseHandler):
        serializer_class = mock_serializer
        tag = "test_handler"

    return TestHandler


@pytest.fixture
def taric_schema_tags() -> TTags:
    return make_schema_dataclass(xsd_schema_paths)


@pytest.fixture
def record_group() -> Sequence[str]:
    return TARIC_RECORD_GROUPS["commodities"]


@pytest.fixture
def envelope_measure() -> bytes:
    model = factories.MeasureFactory.create()
    data = model_to_dict(model)
    data.update(
        {
            "record_code": model.record_code,
            "subrecord_code": model.subrecord_code,
            "taric_template": "taric/measure.xml",
        },
    )
    data["goods_nomenclature"] = {"item_id": model.goods_nomenclature.item_id}
    return generate_test_import_xml([data]).read()


@pytest.fixture
def envelope_commodity() -> bytes:
    model = factories.GoodsNomenclatureFactory.create()
    data = model_to_dict(model)
    data.update(
        {
            "record_code": model.record_code,
            "subrecord_code": model.subrecord_code,
            "taric_template": "taric/goods_nomenclature.xml",
        },
    )
    return generate_test_import_xml([data]).read()


@pytest.fixture
def tag_name() -> Tag:
    return Tag(r"quota.event")


@pytest.fixture
def tag_regex() -> Tag:
    return Tag(r"quota.([a-z.]+).event")


@pytest.fixture
def example_goods_taric_file_location():
    root_path = get_project_root()
    src = os.path.join(root_path, "importer/tests/test_files/goods.xml")
    dst = os.path.join(root_path, "tmp/taric/goods.xml")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copyfile(src, dst)
    taric_file_location = dst
    return taric_file_location
