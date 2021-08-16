from typing import Sequence, Type

import pytest
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from common.serializers import TrackedModelSerializerMixin
from common.serializers import ValiditySerializerMixin
from common.tests import factories
from common.tests.models import TestModel1
from importer import models
from importer.handlers import BaseHandler
from importer.namespaces import (
    make_schema_dataclass,
    xsd_schema_paths,
    Tag,
    TTags,
    TARIC_RECORD_GROUPS
)
from importer.nursery import TariffObjectNursery
from importer.nursery import get_nursery
from importer.utils import DispatchedObjectType


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
def handler_class(mock_serializer) -> Type[BaseHandler]:
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
def prepped_handler(object_nursery, handler_class, handler_test_data) -> BaseHandler:
    return handler_class(handler_test_data, object_nursery)


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
    return """<?xml version="1.0" encoding="UTF-8"?>
    <env:envelope id="210056" xmlns="urn:publicid:-:DGTAXUD:TARIC:MESSAGE:1.0" xmlns:env="urn:publicid:-:DGTAXUD:GENERAL:ENVELOPE:1.0">
        <env:transaction id="330833">
            <env:app.message id="581">
                <oub:transmission xmlns:env="urn:publicid:-:DGTAXUD:GENERAL:ENVELOPE:1.0" xmlns:oub="urn:publicid:-:DGTAXUD:TARIC:MESSAGE:1.0">
                    <oub:record>
                        <oub:transaction.id>330833</oub:transaction.id>
                        <oub:record.code>430</oub:record.code>
                        <oub:subrecord.code>00</oub:subrecord.code>
                        <oub:record.sequence.number>1</oub:record.sequence.number>
                        <oub:update.type>3</oub:update.type>
                        <oub:measure></oub:measure>
                    </oub:record>
                </oub:transmission>
            </env:app.message>
        </env:transaction>
    </env:envelope>""".encode()


@pytest.fixture
def envelope_commodity() -> bytes:
    return """<?xml version="1.0" encoding="UTF-8"?>
    <env:envelope id="210056" xmlns="urn:publicid:-:DGTAXUD:TARIC:MESSAGE:1.0" xmlns:env="urn:publicid:-:DGTAXUD:GENERAL:ENVELOPE:1.0">
        <env:transaction id="330663">
            <env:app.message id="1">
                <oub:transmission xmlns:env="urn:publicid:-:DGTAXUD:GENERAL:ENVELOPE:1.0" xmlns:oub="urn:publicid:-:DGTAXUD:TARIC:MESSAGE:1.0">
                    <oub:record>
                        <oub:transaction.id>330663</oub:transaction.id>
                        <oub:record.code>400</oub:record.code>
                        <oub:subrecord.code>00</oub:subrecord.code>
                        <oub:record.sequence.number>1</oub:record.sequence.number>
                        <oub:update.type>3</oub:update.type>
                        <oub:goods.nomenclature></oub:goods.nomenclature>
                    </oub:record>
                </oub:transmission>
            </env:app.message>
        </env:transaction>
    </env:envelope>""".encode()


@pytest.fixture
def tag_name() -> Tag:
    return Tag(name=r"quota.event")


@pytest.fixture
def tag_regex() -> Tag:
    return Tag(name=r"quota.([a-z.]+).event")
