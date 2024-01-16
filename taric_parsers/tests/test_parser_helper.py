from datetime import date

import pytest

from common.util import TaricDateRange
from taric_parsers.parser_model_link import ModelLink
from taric_parsers.parser_model_link import ModelLinkField
from taric_parsers.parsers.additional_code_parsers import (  # noqa
    AdditionalCodeDescriptionParserV2,
)
from taric_parsers.parsers.additional_code_parsers import (  # noqa
    AdditionalCodeDescriptionPeriodParserV2,
)
from taric_parsers.parsers.additional_code_parsers import AdditionalCodeParserV2  # noqa
from taric_parsers.parsers.additional_code_parsers import (  # noqa
    AdditionalCodeTypeDescriptionParserV2,
)
from taric_parsers.parsers.additional_code_parsers import (  # noqa
    AdditionalCodeTypeParserV2,
)
from taric_parsers.parsers.additional_code_parsers import (  # noqa
    FootnoteAssociationAdditionalCodeParserV2,
)
from taric_parsers.parsers.certificate_parser import (  # noqa
    CertificateDescriptionParserV2,
)
from taric_parsers.parsers.certificate_parser import (  # noqa
    CertificateDescriptionPeriodParserV2,
)
from taric_parsers.parsers.certificate_parser import CertificateParserV2  # noqa
from taric_parsers.parsers.certificate_parser import (  # noqa
    CertificateTypeDescriptionParserV2,
)
from taric_parsers.parsers.certificate_parser import CertificateTypeParserV2  # noqa
from taric_parsers.parsers.commodity_parser import (  # noqa
    FootnoteAssociationGoodsNomenclatureParserV2,
)
from taric_parsers.parsers.commodity_parser import (  # noqa
    GoodsNomenclatureDescriptionParserV2,
)
from taric_parsers.parsers.commodity_parser import (  # noqa
    GoodsNomenclatureDescriptionPeriodParserV2,
)
from taric_parsers.parsers.commodity_parser import (  # noqa
    GoodsNomenclatureIndentParserV2,
)
from taric_parsers.parsers.commodity_parser import (  # noqa
    GoodsNomenclatureOriginParserV2,
)
from taric_parsers.parsers.commodity_parser import GoodsNomenclatureParserV2  # noqa
from taric_parsers.parsers.commodity_parser import (  # noqa
    GoodsNomenclatureSuccessorParserV2,
)
from taric_parsers.parsers.footnote_parser import FootnoteDescriptionParserV2  # noqa
from taric_parsers.parsers.footnote_parser import (  # noqa
    FootnoteDescriptionPeriodParserV2,
)
from taric_parsers.parsers.footnote_parser import FootnoteParserV2  # noqa
from taric_parsers.parsers.footnote_parser import (  # noqa
    FootnoteTypeDescriptionParserV2,
)
from taric_parsers.parsers.footnote_parser import FootnoteTypeParserV2  # noqa
from taric_parsers.parsers.geo_area_parser import (  # noqa
    GeographicalAreaDescriptionParserV2,
)
from taric_parsers.parsers.geo_area_parser import (  # noqa
    GeographicalAreaDescriptionPeriodParserV2,
)
from taric_parsers.parsers.geo_area_parser import GeographicalAreaParserV2  # noqa
from taric_parsers.parsers.geo_area_parser import GeographicalMembershipParserV2  # noqa
from taric_parsers.parsers.measure_parser import (  # noqa
    AdditionalCodeTypeMeasureTypeParserV2,
)
from taric_parsers.parsers.measure_parser import (  # noqa
    DutyExpressionDescriptionParserV2,
)
from taric_parsers.parsers.measure_parser import DutyExpressionParserV2  # noqa
from taric_parsers.parsers.measure_parser import (  # noqa
    FootnoteAssociationMeasureParserV2,
)
from taric_parsers.parsers.measure_parser import (  # noqa
    MeasureActionDescriptionParserV2,
)
from taric_parsers.parsers.measure_parser import MeasureActionParserV2  # noqa
from taric_parsers.parsers.measure_parser import MeasureComponentParserV2  # noqa
from taric_parsers.parsers.measure_parser import (  # noqa
    MeasureConditionCodeDescriptionParserV2,
)
from taric_parsers.parsers.measure_parser import MeasureConditionCodeParserV2  # noqa
from taric_parsers.parsers.measure_parser import (  # noqa
    MeasureConditionComponentParserV2,
)
from taric_parsers.parsers.measure_parser import MeasureConditionParserV2  # noqa
from taric_parsers.parsers.measure_parser import (  # noqa
    MeasureExcludedGeographicalAreaParserV2,
)
from taric_parsers.parsers.measure_parser import MeasurementParserV2  # noqa
from taric_parsers.parsers.measure_parser import (  # noqa
    MeasurementUnitDescriptionParserV2,
)
from taric_parsers.parsers.measure_parser import MeasurementUnitParserV2  # noqa
from taric_parsers.parsers.measure_parser import (  # noqa
    MeasurementUnitQualifierDescriptionParserV2,
)
from taric_parsers.parsers.measure_parser import (  # noqa
    MeasurementUnitQualifierParserV2,
)
from taric_parsers.parsers.measure_parser import MeasureParserV2  # noqa
from taric_parsers.parsers.measure_parser import MeasureTypeDescriptionParserV2  # noqa
from taric_parsers.parsers.measure_parser import MeasureTypeParserV2  # noqa
from taric_parsers.parsers.measure_parser import (  # noqa
    MeasureTypeSeriesDescriptionParserV2,
)
from taric_parsers.parsers.measure_parser import MeasureTypeSeriesParserV2  # noqa
from taric_parsers.parsers.measure_parser import MonetaryUnitDescriptionParserV2  # noqa
from taric_parsers.parsers.measure_parser import MonetaryUnitParserV2  # noqa
from taric_parsers.parsers.quota_parser import QuotaAssociationParserV2  # noqa
from taric_parsers.parsers.quota_parser import QuotaBalanceEventParserV2  # noqa
from taric_parsers.parsers.quota_parser import QuotaBlockingParserV2  # noqa
from taric_parsers.parsers.quota_parser import (  # noqa
    QuotaClosedAndTransferredEventParserV2,
)
from taric_parsers.parsers.quota_parser import QuotaCriticalEventParserV2  # noqa
from taric_parsers.parsers.quota_parser import QuotaDefinitionParserV2  # noqa
from taric_parsers.parsers.quota_parser import QuotaEventParserV2  # noqa
from taric_parsers.parsers.quota_parser import QuotaExhaustionEventParserV2  # noqa
from taric_parsers.parsers.quota_parser import (  # noqa
    QuotaOrderNumberOriginExclusionParserV2,
)
from taric_parsers.parsers.quota_parser import QuotaOrderNumberOriginParserV2  # noqa
from taric_parsers.parsers.quota_parser import QuotaOrderNumberParserV2  # noqa
from taric_parsers.parsers.quota_parser import QuotaReopeningEventParserV2  # noqa
from taric_parsers.parsers.quota_parser import QuotaSuspensionParserV2  # noqa
from taric_parsers.parsers.quota_parser import QuotaUnblockingEventParserV2  # noqa
from taric_parsers.parsers.quota_parser import QuotaUnsuspensionEventParserV2  # noqa
from taric_parsers.parsers.regulation_parser import BaseRegulationParserV2  # noqa
from taric_parsers.parsers.regulation_parser import (  # noqa
    FullTemporaryStopActionParserV2,
)
from taric_parsers.parsers.regulation_parser import (  # noqa
    FullTemporaryStopRegulationParserV2,
)
from taric_parsers.parsers.regulation_parser import (  # noqa
    ModificationRegulationParserV2,
)
from taric_parsers.parsers.regulation_parser import (  # noqa
    RegulationGroupDescriptionParserV2,
)
from taric_parsers.parsers.regulation_parser import RegulationGroupParserV2  # noqa
from taric_parsers.parsers.regulation_parser import (  # noqa
    RegulationReplacementParserV2,
)
from taric_parsers.parsers.taric_parser import BaseTaricParser
from taric_parsers.parsers.taric_parser import ParserHelper

pytestmark = pytest.mark.django_db


@pytest.mark.importer_v2
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
