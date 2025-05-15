import os
import shutil
import xml.etree.ElementTree as et
from collections.abc import Generator
from pathlib import Path
from typing import Sequence
from typing import Type

import pytest
from django.core.management import BaseCommand
from django.forms.models import model_to_dict
from rest_framework import serializers
from rest_framework.serializers import ListSerializer
from rest_framework.serializers import ModelSerializer

from common.serializers import TrackedModelSerializerMixin
from common.serializers import ValiditySerializerMixin
from common.tests import factories
from common.tests.models import TestModel1
from common.tests.util import generate_test_import_xml
from importer import models
from importer.handlers import BaseHandler
from importer.namespaces import TARIC_RECORD_GROUPS
from importer.namespaces import Tag
from importer.namespaces import TTags
from importer.namespaces import make_schema_dataclass
from importer.namespaces import xsd_schema_paths
from importer.nursery import TariffObjectNursery
from importer.nursery import get_nursery
from importer.utils import DispatchedObjectType


def get_project_root():
    return Path(__file__).parents[2]


@pytest.fixture
def object_nursery() -> Generator[TariffObjectNursery, None, None]:
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
def mock_list_serializer() -> Type[ListSerializer]:
    class TestListSerializer(ValiditySerializerMixin):
        def __init__(self):
            pass

    return TestListSerializer


@pytest.fixture
def parser_class(mock_serializer) -> Type[BaseHandler]:
    class TestHandler(BaseHandler):
        serializer_class = mock_serializer
        tag = "test_handler"

    return TestHandler


@pytest.fixture
def handler_class_with_dependencies(mock_serializer) -> Type[BaseHandler]:
    class TestHandler2(BaseHandler):
        serializer_class = mock_serializer
        tag = "test_handler_dep2"

    @TestHandler2.register_dependant
    class TestHandler1(BaseHandler):
        dependencies = [TestHandler2]
        serializer_class = mock_serializer
        tag = "test_handler_dep1"

    return TestHandler1


@pytest.fixture
def handler_class_with_links(mock_serializer) -> Type[BaseHandler]:
    class TestHandler(BaseHandler):
        links = [
            {
                "model": TestModel1,
                "name": "test_model_1",
            },
        ]
        serializer_class = mock_serializer
        tag = "test_handler"

    return TestHandler


@pytest.fixture
def handler_test_data(approved_transaction, date_ranges) -> DispatchedObjectType:
    return {
        "data": {
            "sid": 99999,
            "name": "test_handlers",
            "update_type": 3,
            "valid_between": {
                "upper": date_ranges.normal.upper,
                "lower": date_ranges.normal.lower,
            },
            "transaction_id": approved_transaction.pk,
        },
        "tag": "",
        "transaction_id": approved_transaction.pk,
    }


@pytest.fixture
def handler_footnote_type_test_data(
    approved_transaction,
    date_ranges,
) -> DispatchedObjectType:
    return {
        "data": {
            "footnote_type_id": "ZZ",
            "application_code": 1,
            "description": "testing",
            "update_type": 3,
            "valid_between": {
                "upper": date_ranges.normal.upper,
                "lower": date_ranges.normal.lower,
            },
            "transaction_id": approved_transaction.pk,
        },
        "tag": "footnote.type",
        "transaction_id": approved_transaction.pk,
    }


@pytest.fixture
def handler_footnote_type_description_test_data(
    approved_transaction,
    date_ranges,
) -> DispatchedObjectType:
    return {
        "data": {
            "footnote_type_id": "ZZ",
            "description": "testing",
            "update_type": 3,
            "transaction_id": approved_transaction.pk,
        },
        "tag": "footnote.type.description",
        "transaction_id": approved_transaction.pk,
    }


@pytest.fixture
def prepped_handler(object_nursery, parser_class, handler_test_data) -> BaseHandler:
    return parser_class(handler_test_data, object_nursery)


@pytest.fixture
def prepped_handler_with_dependencies1(
    object_nursery,
    handler_class_with_dependencies,
    handler_test_data,
) -> BaseHandler:
    return handler_class_with_dependencies(handler_test_data, object_nursery)


@pytest.fixture
def prepped_handler_with_dependencies2(
    prepped_handler_with_dependencies1,
) -> BaseHandler:
    return prepped_handler_with_dependencies1.dependencies[0](
        prepped_handler_with_dependencies1.serialize(),
        prepped_handler_with_dependencies1.nursery,
    )


@pytest.fixture
def prepped_handler_with_link(
    handler_class_with_links,
    object_nursery,
    handler_test_data,
) -> BaseHandler:
    handler_test_data["data"]["test_model_1__sid"] = factories.TestModel1Factory().sid

    return handler_class_with_links(handler_test_data, object_nursery)


@pytest.fixture
def chunk() -> models.ImporterXMLChunk:
    return factories.ImporterXMLChunkFactory.create()


@pytest.fixture
def goods_description_only_update_xml_as_text():
    src = os.path.join(
        get_project_root(),
        "importer/tests/test_files/goods_description_only_update.xml",
    )
    xml_text = open(src).read()
    return xml_text


@pytest.fixture
def goods_description_with_period_create_xml_as_text():
    src = os.path.join(
        get_project_root(),
        "importer/tests/test_files/goods_description_with_period_create_same_transaction.xml",
    )
    xml_text = open(src).read()
    return xml_text


@pytest.fixture
def goods_description_with_period_create_period_first_xml_as_text():
    src = os.path.join(
        get_project_root(),
        "importer/tests/test_files/goods_description_with_period_create_same_transaction_period_first.xml",
    )
    xml_text = open(src).read()
    return xml_text


@pytest.fixture
def goods_description_only_create_xml_as_text():
    src = os.path.join(
        get_project_root(),
        "importer/tests/test_files/goods_description_no_period_create.xml",
    )
    xml_text = open(src).read()
    return xml_text


@pytest.fixture
def create_goods_xml_as_text():
    src = os.path.join(
        get_project_root(),
        "importer/tests/test_files/goods.xml",
    )
    xml_text = open(src).read()
    return xml_text


@pytest.fixture
def batch() -> models.ImportBatch:
    return factories.ImportBatchFactory.create()


@pytest.fixture
def batch_dependency() -> models.BatchDependencies:
    dependencies = factories.BatchDependenciesFactory.create()
    factories.ImporterXMLChunkFactory.create(batch=dependencies.depends_on)
    factories.ImporterXMLChunkFactory.create(batch=dependencies.dependent_batch)
    return dependencies


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


@pytest.fixture
def goods_xml_element_tree():
    src = os.path.join(get_project_root(), "importer/tests/test_files/goods.xml")
    xml_text = open(src).read()
    return et.fromstring(xml_text)


@pytest.fixture
def goods_indents_xml_element_tree():
    src = os.path.join(
        get_project_root(),
        "importer/tests/test_files/goods_indents.xml",
    )
    xml_text = open(src).read()
    return et.fromstring(xml_text)


def get_command_help_text(capsys, command, command_class=BaseCommand):
    captured = capsys.readouterr()
    command_class().print_help(command, "")
    return captured.out


@pytest.fixture
def test_files_path():
    return os.path.abspath(
        os.path.join(os.path.dirname(__file__), "test_files"),
    )
