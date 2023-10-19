import pytest

from common.util import TaricDateRange
from taric_parsers.parsers.additional_code_parsers import *
from taric_parsers.parsers.certificate_parser import *
from taric_parsers.parsers.footnote_parser import *
from taric_parsers.parsers.geo_area_parser import *
from taric_parsers.parsers.measure_parser import *
from taric_parsers.parsers.quota_parser import *
from taric_parsers.parsers.regulation_parser import *

pytestmark = pytest.mark.django_db


class TestParserHelper:
    def test_get_parser_by_model(self):
        class MadeUpModel:
            sequence_number: int = None
            transaction_id: int = None
            valid_between: TaricDateRange = None

            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)

        class TestParentElementParser(BaseTaricParser):
            xml_object_tag = "test.parent.element"

            record_code = "900"
            subrecord_code = "100"
            valid_between = None
            valid_between_lower: date = None
            valid_between_upper: date = None
            invalid_property: str = None
            model = MadeUpModel

            def __init__(self):
                super().__init__()

        target = ParserHelper.get_parser_by_model

        result = target(MadeUpModel)

        assert result == TestParentElementParser

    def test_get_parser_by_model_errors_with_no_match(self):
        class MadeUpModel:
            sequence_number: int = None
            transaction_id: int = None
            valid_between: TaricDateRange = None

            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)

        e = None
        with pytest.raises(Exception) as e:
            ParserHelper.get_parser_by_model(MadeUpModel)

        assert "No parser class found for parsing MadeUpModel" in str(e)

    def test_get_child_parsers(self):
        class MadeUpModel:
            def __init__(self):
                self.x = "z"

        class TestParentElementParser(BaseTaricParser):
            model = MadeUpModel
            xml_object_tag = "test.parent.element"

            def __init__(self):
                super().__init__()

        class TestChildElementParser(BaseTaricParser):
            model = MadeUpModel
            parent_parser = TestParentElementParser
            model_links = [
                ModelLink(
                    MadeUpModel,
                    [
                        ModelLinkField("parent_field_1", "field_1"),
                    ],
                    "test.parent.element",
                ),
            ]

            def __init__(self):
                super().__init__()

        result = ParserHelper.get_child_parsers(TestParentElementParser())

        assert result[0] == TestChildElementParser

    def test_get_child_parsers_empty_list_when_no_children(self):
        class MadeUpModel:
            def __init__(self):
                self.x = "z"

        class TestParentElementParser(BaseTaricParser):
            model = MadeUpModel
            xml_object_tag = "test.parent.element"

            def __init__(self):
                super().__init__()

        result = ParserHelper.get_child_parsers(TestParentElementParser())

        assert len(result) == 0

    def test_get_parser_by_tag(self):
        class MadeUpModel:
            def __init__(self):
                self.x = "z"

        class TestParentElementParser(BaseTaricParser):
            model = MadeUpModel
            xml_object_tag = "test.parent.element.zzz"

            def __init__(self):
                super().__init__()

        matched_parser = ParserHelper.get_parser_by_tag(
            TestParentElementParser.xml_object_tag,
        )

        assert matched_parser == TestParentElementParser

    def test_get_parser_by_tag_raises_exception_if_no_match(self):
        with pytest.raises(Exception) as e:
            ParserHelper.get_parser_by_tag("some.nonexistant.tag")

        assert "No parser class matching some.nonexistant.tag" in str(e)

    def test_get_parser_classes(self):
        target = ParserHelper.get_parser_classes()

        assert len(target) > 65

    def test_subclasses_for(self):
        target = ParserHelper.subclasses_for(BaseTaricParser)

        assert len(target) > 65
