import pytest
from rest_framework.exceptions import ValidationError

from common.tests import factories
from common.tests.models import TestModel1
from importer import handlers
from importer.handlers import BaseHandler, MismatchedSerializerError

pytestmark = pytest.mark.django_db


def test_handler_registers_on_definition(object_nursery, mock_serializer):
    assert "test_handler_registers_on_definition" not in object_nursery.handlers

    class TestHandler(handlers.BaseHandler):
        serializer_class = mock_serializer
        tag = "test_handler_registers_on_definition"

    assert "test_handler_registers_on_definition" in object_nursery.handlers

    assert (
        object_nursery.get_handler("test_handler_registers_on_definition")
        is TestHandler
    )


def test_handler_validates_clean_data(prepped_handler):
    prepped_handler.clean(prepped_handler.data)


def test_handler_raises_error_validating_dirty_data(prepped_handler):
    data = prepped_handler.data
    data.pop("update_type")

    with pytest.raises(ValidationError):
        prepped_handler.clean(data)


def test_handler_pre_save(prepped_handler):
    data = {"a": 1, "b": 2}
    links = {"c": 3, "d": 4}

    merged_data = prepped_handler.pre_save(data, links)

    assert merged_data == {"a": 1, "b": 2, "c": 3, "d": 4}


def test_handler_custom_pre_save(mock_serializer, handler_test_data, object_nursery):
    class TestCustomPreSaveError(Exception):
        pass

    class TestHandler(BaseHandler):
        links = [
            {
                "model": TestModel1,
                "name": "test_model_1",
            },
        ]
        serializer_class = mock_serializer
        tag = "test_handler"

        def pre_save(self, data, links):
            raise TestCustomPreSaveError

    handler = TestHandler(handler_test_data, object_nursery)

    with pytest.raises(TestCustomPreSaveError):
        handler.dispatch()


def test_handler_custom_post_save(mock_serializer, handler_test_data, object_nursery):
    class TestCustomPostSaveError(Exception):
        pass

    class TestHandler(BaseHandler):
        links = [
            {
                "model": TestModel1,
                "name": "test_model_1",
            },
        ]
        serializer_class = mock_serializer
        tag = "test_handler"

        def post_save(self, obj):
            raise TestCustomPostSaveError

    handler = TestHandler(handler_test_data, object_nursery)

    with pytest.raises(TestCustomPostSaveError):
        handler.dispatch()


def test_generate_dependency_keys(
    prepped_handler_with_dependencies1,
    prepped_handler_with_dependencies2,
):
    assert prepped_handler_with_dependencies1.dependency_keys == {
        prepped_handler_with_dependencies2.key,
    }
    assert prepped_handler_with_dependencies2.dependency_keys == {
        prepped_handler_with_dependencies1.key,
    }


def test_failed_resolve_dependencies_returns_false(prepped_handler_with_dependencies1):
    assert not prepped_handler_with_dependencies1.resolve_dependencies()


def test_resolve_dependencies_returns_true(
    prepped_handler_with_dependencies1,
    prepped_handler_with_dependencies2,
):
    nursery = prepped_handler_with_dependencies1.nursery
    nursery._cache_handler(prepped_handler_with_dependencies2)

    assert prepped_handler_with_dependencies1.resolve_dependencies()


def test_get_generic_link(prepped_handler):
    test_instance = factories.TestModel1Factory()
    obj_instance = prepped_handler.get_generic_link(
        TestModel1,
        {"sid": test_instance.sid},
    )

    assert (test_instance, False) == obj_instance


def test_get_custom_link(mock_serializer, handler_test_data, object_nursery):
    class TestGetCustomLinkError(Exception):
        pass

    class TestHandler(BaseHandler):
        links = [
            {
                "model": TestModel1,
                "name": "test_model_1",
            },
        ]
        serializer_class = mock_serializer
        tag = "test_handler"

        def get_test_model_1_link(self, model, kwargs):
            raise TestGetCustomLinkError

    handler = TestHandler(handler_test_data, object_nursery)
    handler.data["test_model_1__sid"] = 1

    with pytest.raises(TestGetCustomLinkError):
        handler.resolve_links()


def test_resolve_links_returns_true(prepped_handler_with_link):
    assert prepped_handler_with_link.resolve_links()


def test_failed_resolve_links_returns_false(prepped_handler_with_link):
    prepped_handler_with_link.data["test_model_1__sid"] += 1
    assert not prepped_handler_with_link.resolve_links()


def test_failed_optional_resolve_links_returns_true(prepped_handler_with_link):
    prepped_handler_with_link.data["test_model_1__sid"] += 1
    prepped_handler_with_link.links[0]["optional"] = True
    assert prepped_handler_with_link.resolve_links()


def test_dispatch(prepped_handler):
    assert not TestModel1.objects.filter(
        sid=prepped_handler.data["sid"],
        name=prepped_handler.data["name"],
    ).exists()
    prepped_handler.dispatch()
    assert TestModel1.objects.filter(
        sid=prepped_handler.data["sid"],
        name=prepped_handler.data["name"],
    ).exists()


def test_serialize(prepped_handler):
    assert prepped_handler.serialize() == {
        "data": prepped_handler.data,
        "tag": prepped_handler.tag,
        "transaction_id": prepped_handler.transaction_id,
    }


def test_register_multiple_dependencies(mock_serializer):
    class TestHandler(BaseHandler):
        serializer_class = mock_serializer
        tag = "test_handler_dep2"

    @TestHandler.register_dependant
    class TestHandlerChild1(BaseHandler):
        dependencies = [TestHandler]
        serializer_class = mock_serializer
        tag = "test_handler_dep1"

    @TestHandler.register_dependant
    class TestHandlerChild2(BaseHandler):
        dependencies = [TestHandler]
        serializer_class = mock_serializer
        tag = "test_handler_dep1"

    print(TestHandler.dependencies)

    assert TestHandlerChild1 in TestHandler.dependencies
    assert TestHandlerChild2 in TestHandler.dependencies


def test_register_multiple_dependencies_with_different_serializers(
    mock_serializer, mock_list_serializer, handler_test_data, object_nursery
):
    class TestHandler(BaseHandler):
        serializer_class = mock_serializer
        tag = "test_handler_dep2"

    @TestHandler.register_dependant
    class TestHandlerChild1(BaseHandler):
        dependencies = [TestHandler]
        serializer_class = mock_list_serializer
        tag = "test_handler_dep1"

    @TestHandler.register_dependant
    class TestHandlerChild2(BaseHandler):
        dependencies = [TestHandler]
        serializer_class = mock_serializer
        tag = "test_handler_dep1"

    print(TestHandler.dependencies)
    ex = None
    with pytest.raises(MismatchedSerializerError) as ex:
        x = TestHandler(handler_test_data, object_nursery)

    assert (
        str(ex.value)
        == f"Dependent parsers must have the same serializer_class as their dependencies. "
        f"Dependency TestHandlerChild1 has "
        f"serializer_class TestListSerializer. "
        f"TestHandler has serializer_class TestSerializer."
    )


def test_base_handler_meta_no_type():
    ex = None
    with pytest.raises(AttributeError) as ex:

        class NotAHandler(BaseHandler):
            def __init__(self):
                pass

    assert str(ex.value) == 'NotAHandler requires attribute "tag" to be a str.'


def test_base_handler_meta_new_check_type():
    ex = None
    with pytest.raises(AttributeError) as ex:

        class NotAHandler(BaseHandler):
            tag: int = None

            def __init__(self):
                pass

    assert str(ex.value) == 'NotAHandler requires attribute "tag" to be a str.'


def test_base_handler_check_serializer():
    class NotASerializer:
        def __init__(self):
            pass

    ex = None
    with pytest.raises(AttributeError) as ex:

        class NotAHandler(BaseHandler):
            tag: str = "dfgdfgdf"
            serializer_class = NotASerializer

            def __init__(self):
                pass

    assert (
        str(ex.value)
        == 'NotAHandler requires attribute "serializer_class" to be a subclass of "ModelSerializer".'
    )
