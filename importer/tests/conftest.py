from typing import Type

import pytest
from rest_framework.serializers import ModelSerializer

from common.tests import factories
from common.tests.models import TestModel1
from importer.handlers import BaseHandler
from importer.nursery import get_nursery
from importer.nursery import TariffObjectNursery
from importer.utils import DispatchedObjectType


@pytest.fixture
def object_nursery() -> TariffObjectNursery:
    return get_nursery()


@pytest.fixture
def mock_serializer() -> Type[ModelSerializer]:
    class TestSerializer(ModelSerializer):
        class Meta:
            model = TestModel1
            fields = "__all__"

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
            }
        ]
        serializer_class = mock_serializer
        tag = "test_handler"

    return TestHandler


@pytest.fixture
def handler_test_data(approved_workbasket, date_ranges) -> DispatchedObjectType:
    data = {
        "data": {
            "sid": 99999,
            "name": "test_handlers",
            "update_type": 3,
            "valid_between": {
                "upper": date_ranges.normal.upper,
                "lower": date_ranges.normal.lower,
            },
            "workbasket": approved_workbasket.pk,
        },
        "tag": "",
        "workbasket_id": approved_workbasket.pk,
    }

    return data


@pytest.fixture
def prepped_handler(object_nursery, handler_class, handler_test_data) -> BaseHandler:
    return handler_class(handler_test_data, object_nursery)


@pytest.fixture
def prepped_handler_with_dependencies1(
    object_nursery, handler_class_with_dependencies, handler_test_data
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
    handler_class_with_links, object_nursery, handler_test_data
) -> BaseHandler:
    handler_test_data["data"]["test_model_1__sid"] = factories.TestModel1Factory().sid

    return handler_class_with_links(handler_test_data, object_nursery)
