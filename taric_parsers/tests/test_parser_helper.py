from datetime import date

import pytest

from common.util import TaricDateRange
from taric_parsers.parser_model_link import ModelLink
from taric_parsers.parser_model_link import ModelLinkField
from taric_parsers.parsers.additional_code_parsers import (  # noqa
    NewAdditionalCodeDescriptionParser,
)
from taric_parsers.parsers.additional_code_parsers import (  # noqa
    NewAdditionalCodeDescriptionPeriodParser,
)
from taric_parsers.parsers.additional_code_parsers import (  # noqa
    NewAdditionalCodeParser,
)
from taric_parsers.parsers.additional_code_parsers import (  # noqa
    NewAdditionalCodeTypeDescriptionParser,
)
from taric_parsers.parsers.additional_code_parsers import (  # noqa
    NewAdditionalCodeTypeParser,
)
from taric_parsers.parsers.additional_code_parsers import (  # noqa
    NewFootnoteAssociationAdditionalCodeParser,
)
from taric_parsers.parsers.certificate_parser import (  # noqa
    NewCertificateDescriptionParser,
)
from taric_parsers.parsers.certificate_parser import (  # noqa
    NewCertificateDescriptionPeriodParser,
)
from taric_parsers.parsers.certificate_parser import NewCertificateParser  # noqa
from taric_parsers.parsers.certificate_parser import (  # noqa
    NewCertificateTypeDescriptionParser,
)
from taric_parsers.parsers.certificate_parser import NewCertificateTypeParser  # noqa
from taric_parsers.parsers.commodity_parser import (  # noqa
    NewFootnoteAssociationGoodsNomenclatureParser,
)
from taric_parsers.parsers.commodity_parser import (  # noqa
    NewGoodsNomenclatureDescriptionParser,
)
from taric_parsers.parsers.commodity_parser import (  # noqa
    NewGoodsNomenclatureDescriptionPeriodParser,
)
from taric_parsers.parsers.commodity_parser import (  # noqa
    NewGoodsNomenclatureIndentParser,
)
from taric_parsers.parsers.commodity_parser import (  # noqa
    NewGoodsNomenclatureOriginParser,
)
from taric_parsers.parsers.commodity_parser import NewGoodsNomenclatureParser  # noqa
from taric_parsers.parsers.commodity_parser import (  # noqa
    NewGoodsNomenclatureSuccessorParser,
)
from taric_parsers.parsers.footnote_parser import NewFootnoteDescriptionParser  # noqa
from taric_parsers.parsers.footnote_parser import (  # noqa
    NewFootnoteDescriptionPeriodParser,
)
from taric_parsers.parsers.footnote_parser import NewFootnoteParser  # noqa
from taric_parsers.parsers.footnote_parser import (  # noqa
    NewFootnoteTypeDescriptionParser,
)
from taric_parsers.parsers.footnote_parser import NewFootnoteTypeParser  # noqa
from taric_parsers.parsers.geo_area_parser import (  # noqa
    NewGeographicalAreaDescriptionParser,
)
from taric_parsers.parsers.geo_area_parser import (  # noqa
    NewGeographicalAreaDescriptionPeriodParser,
)
from taric_parsers.parsers.geo_area_parser import NewGeographicalAreaParser  # noqa
from taric_parsers.parsers.geo_area_parser import (  # noqa
    NewGeographicalMembershipParser,
)
from taric_parsers.parsers.measure_parser import (  # noqa
    NewAdditionalCodeTypeMeasureTypeParser,
)
from taric_parsers.parsers.measure_parser import (  # noqa
    NewDutyExpressionDescriptionParser,
)
from taric_parsers.parsers.measure_parser import NewDutyExpressionParser  # noqa
from taric_parsers.parsers.measure_parser import (  # noqa
    NewFootnoteAssociationMeasureParser,
)
from taric_parsers.parsers.measure_parser import (  # noqa
    NewMeasureActionDescriptionParser,
)
from taric_parsers.parsers.measure_parser import NewMeasureActionParser  # noqa
from taric_parsers.parsers.measure_parser import NewMeasureComponentParser  # noqa
from taric_parsers.parsers.measure_parser import (  # noqa
    NewMeasureConditionCodeDescriptionParser,
)
from taric_parsers.parsers.measure_parser import NewMeasureConditionCodeParser  # noqa
from taric_parsers.parsers.measure_parser import (  # noqa
    NewMeasureConditionComponentParser,
)
from taric_parsers.parsers.measure_parser import NewMeasureConditionParser  # noqa
from taric_parsers.parsers.measure_parser import (  # noqa
    NewMeasureExcludedGeographicalAreaParser,
)
from taric_parsers.parsers.measure_parser import NewMeasurementParser  # noqa
from taric_parsers.parsers.measure_parser import (  # noqa
    NewMeasurementUnitDescriptionParser,
)
from taric_parsers.parsers.measure_parser import NewMeasurementUnitParser  # noqa
from taric_parsers.parsers.measure_parser import (  # noqa
    NewMeasurementUnitQualifierDescriptionParser,
)
from taric_parsers.parsers.measure_parser import (  # noqa
    NewMeasurementUnitQualifierParser,
)
from taric_parsers.parsers.measure_parser import NewMeasureParser  # noqa
from taric_parsers.parsers.measure_parser import NewMeasureTypeDescriptionParser  # noqa
from taric_parsers.parsers.measure_parser import NewMeasureTypeParser  # noqa
from taric_parsers.parsers.measure_parser import (  # noqa
    NewMeasureTypeSeriesDescriptionParser,
)
from taric_parsers.parsers.measure_parser import NewMeasureTypeSeriesParser  # noqa
from taric_parsers.parsers.measure_parser import (  # noqa
    NewMonetaryUnitDescriptionParser,
)
from taric_parsers.parsers.measure_parser import NewMonetaryUnitParser  # noqa
from taric_parsers.parsers.quota_parser import NewQuotaAssociationParser  # noqa
from taric_parsers.parsers.quota_parser import NewQuotaBalanceEventParser  # noqa
from taric_parsers.parsers.quota_parser import NewQuotaBlockingParser  # noqa
from taric_parsers.parsers.quota_parser import (  # noqa
    NewQuotaClosedAndTransferredEventParser,
)
from taric_parsers.parsers.quota_parser import NewQuotaCriticalEventParser  # noqa
from taric_parsers.parsers.quota_parser import NewQuotaDefinitionParser  # noqa
from taric_parsers.parsers.quota_parser import NewQuotaEventParser  # noqa
from taric_parsers.parsers.quota_parser import NewQuotaExhaustionEventParser  # noqa
from taric_parsers.parsers.quota_parser import (  # noqa
    NewQuotaOrderNumberOriginExclusionParser,
)
from taric_parsers.parsers.quota_parser import NewQuotaOrderNumberOriginParser  # noqa
from taric_parsers.parsers.quota_parser import NewQuotaOrderNumberParser  # noqa
from taric_parsers.parsers.quota_parser import NewQuotaReopeningEventParser  # noqa
from taric_parsers.parsers.quota_parser import NewQuotaSuspensionParser  # noqa
from taric_parsers.parsers.quota_parser import NewQuotaUnblockingEventParser  # noqa
from taric_parsers.parsers.quota_parser import NewQuotaUnsuspensionEventParser  # noqa
from taric_parsers.parsers.regulation_parser import NewBaseRegulationParser  # noqa
from taric_parsers.parsers.regulation_parser import (  # noqa
    NewFullTemporaryStopActionParser,
)
from taric_parsers.parsers.regulation_parser import (  # noqa
    NewFullTemporaryStopRegulationParser,
)
from taric_parsers.parsers.regulation_parser import (  # noqa
    NewModificationRegulationParser,
)
from taric_parsers.parsers.regulation_parser import (  # noqa
    NewRegulationGroupDescriptionParser,
)
from taric_parsers.parsers.regulation_parser import NewRegulationGroupParser  # noqa
from taric_parsers.parsers.regulation_parser import (  # noqa
    NewRegulationReplacementParser,
)
from taric_parsers.parsers.taric_parser import BaseTaricParser
from taric_parsers.parsers.taric_parser import ParserHelper

pytestmark = pytest.mark.django_db


@pytest.mark.new_importer
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
