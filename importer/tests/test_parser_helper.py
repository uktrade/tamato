import pytest

from additional_codes.new_import_parsers import *
from certificates.new_import_parsers import *
from commodities.new_import_parsers import *
from common.util import TaricDateRange
from footnotes.new_import_parsers import *
from geo_areas.new_import_parsers import *
from importer.new_parsers import ParserHelper
from measures.new_import_parsers import *
from quotas.new_import_parsers import *
from regulations.new_import_parsers import *

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

        class TestParentElementParser(NewElementParser):
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

        target = ParserHelper.get_parser_by_model

        e = None
        with pytest.raises(Exception) as e:
            target(MadeUpModel)

        assert "No parser class found for parsing MadeUpModel" in str(e)
