from datetime import date
from typing import List

import pytest

from additional_codes.models import AdditionalCodeType
from common.tests import factories
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
class TestNewElementParser:
    def test_init_defaults(self):
        target = BaseTaricParser

        assert target.model is None
        assert target.issues == []
        assert target.transaction_id is None
        assert target.record_code is None
        assert target.subrecord_code is None
        assert target.xml_object_tag is None
        assert target.update_type is None
        assert target.update_type_name is None
        assert target.links_valid is None
        assert target.value_mapping == {}
        assert target.model_links == []
        assert target.parent_parser is None
        assert target.parent_handler is None
        assert target.xml_object_tag is None

    def test_links_raises_exception(self):
        target = BaseTaricParser()

        with pytest.raises(Exception) as e:
            target.links()
            assert str(e) == "No parser defined for NewElementParser, is this correct?"

    def test_links_does_not_raises_exception_when_populated(self):
        class TestElementParser(BaseTaricParser):
            def __init__(self):
                super().__init__()
                self.model_links = []

        target = TestElementParser()

        assert target.links() == []

    def test_missing_child_attributes_returns_none_when_has_no_children(self):
        target = BaseTaricParser()

        assert target.missing_child_attributes() is None

    def test_missing_child_attributes_returns_dict_when_has_children(self):
        # setup parent
        class MadeUpModel:
            model_links = []

            def __init__(self):
                self.x = "z"

        class TestParentElementParser(BaseTaricParser):
            model = MadeUpModel
            xml_object_tag = "test.parent.element"

            def __init__(self):
                super().__init__()
                self.field_1 = None

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
                self.parent_field_1 = "zzz"

        target = TestParentElementParser()
        assert TestChildElementParser in ParserHelper.get_parser_classes()
        assert len(ParserHelper.get_child_parsers(target)) == 1
        #
        assert target.missing_child_attributes() == {
            "TestChildElementParser": ["parent_field_1"],
        }

    def test_missing_child_attributes_errors_when_attribute_not_present_on_parent(self):
        # setup parent
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
                self.parent_field_1 = "zzz"

        target = TestParentElementParser()

        e = None
        with pytest.raises(Exception) as e:
            target.missing_child_attributes()

        assert "Field referenced by child TestChildElementParser" in str(e)
        assert "field_1 does not exist on parent TestParentElementParser" in str(e)

    def test_identity_fields_for_parent_raises_error_if_no_parent_parser(self):
        class MadeUpModel:
            def __init__(self):
                self.x = "z"

        class TestParentElementParser(BaseTaricParser):
            model = MadeUpModel
            xml_object_tag = "test.parent.element"

            def __init__(self):
                super().__init__()

        target = TestParentElementParser()

        e = None
        with pytest.raises(Exception) as e:
            target.identity_fields_for_parent()

        assert "Model TestParentElementParser has no parent parser" in str(e)

    def test_identity_fields_for_parent_raises_error_if_no_model_links(self):
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
            model_links = []

            def __init__(self):
                super().__init__()
                self.parent_field_1 = "zzz"

        target = TestChildElementParser()

        e = None
        with pytest.raises(Exception) as e:
            target.identity_fields_for_parent()

        assert (
            "Model TestChildElementParser appears to have a parent parser but no model links"
            in str(e)
        )

    def test_identity_fields_for_parent_raises_error_if_no_model_link_to_parent(self):
        class MadeUpModel:
            def __init__(self):
                self.x = "z"

        class AnotherMadeUpModel:
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
                    AnotherMadeUpModel,
                    [
                        ModelLinkField("parent_field_1", "field_1"),
                    ],
                    "test.parent.element",
                ),
            ]

            def __init__(self):
                super().__init__()
                self.parent_field_1 = "zzz"

        target = TestChildElementParser()

        e = None
        with pytest.raises(Exception) as e:
            target.identity_fields_for_parent()

        assert (
            "Model TestChildElementParser appears to not have a model links to the parent model"
            in str(e)
        )

    def test_populate_fails_of_record_code_differs(self):
        class TestParentElementParser(BaseTaricParser):
            xml_object_tag = "test.parent.element"
            record_code = "000"
            subrecord_code = "000"

            def __init__(self):
                super().__init__()

        target = TestParentElementParser()

        e = None
        with pytest.raises(Exception) as e:
            target.populate(123, "900", "100", 1, {})

        assert "Record code mismatch : expected : 000, got : 900" in str(e)

    def test_populate_fails_of_sub_record_code_differs(self):
        class TestParentElementParser(BaseTaricParser):
            xml_object_tag = "test.parent.element"

            record_code = "900"
            subrecord_code = "100"

            def __init__(self):
                super().__init__()

        target = TestParentElementParser()

        e = None
        with pytest.raises(Exception) as e:
            target.populate(123, "900", "200", 1, {})

        assert "Sub-record code mismatch : expected : 100, got : 200" in str(e)

    def test_populate_succeeds_when_record_and_subrecord_match(self):
        class TestParentElementParser(BaseTaricParser):
            xml_object_tag = "test.parent.element"

            record_code = "900"
            subrecord_code = "100"

            sid: int = None
            validity_start: date = None

            def __init__(self):
                super().__init__()

        target = TestParentElementParser()

        target.populate(
            123,
            "900",
            "100",
            1,
            {
                "validity_start": "2023-01-01",
                "sid": "123",
            },
        )

        assert target.sid == 123
        assert target.validity_start == date(2023, 1, 1)

    def test_populate_fails_unexpected_fields_are_presented(self):
        class TestParentElementParser(BaseTaricParser):
            xml_object_tag = "test.parent.element"

            record_code = "900"
            subrecord_code = "100"

            sid: int = None
            validity_start: date = None

            def __init__(self):
                super().__init__()

        target = TestParentElementParser()

        e = None
        with pytest.raises(Exception) as e:
            target.populate(
                123,
                "900",
                "100",
                1,
                {
                    "validity_start": "2023-01-01",
                    "sid": "123",
                    "dfgdfg": "dsfgdfg",
                },
            )

        assert "test.parent.element TestParentElementParser " in str(e)
        assert (
            "does not have a dfgdfg attribute, and can't assign value dsfgdfg" in str(e)
        )

    def test_populate_ignores_excluded_fields(self):
        class TestParentElementParser(BaseTaricParser):
            xml_object_tag = "test.parent.element"

            record_code = "900"
            subrecord_code = "100"

            sid: int = None
            validity_start: date = None

            def __init__(self):
                super().__init__()

        target = TestParentElementParser()

        target.populate(
            123,
            "900",
            "100",
            1,
            {
                "validity_start": "2023-01-01",
                "sid": "123",
                "language_id": "fghfgh",
            },
        )

        assert target.sid == 123
        assert target.validity_start == date(2023, 1, 1)

    def test_populate_value_mapped_fields(self):
        class TestParentElementParser(BaseTaricParser):
            xml_object_tag = "test.parent.element"

            record_code = "900"
            subrecord_code = "100"

            another_sid: int = None
            validity_start: date = None
            string_value: str = None
            float_value: float = None

            value_mapping = {
                "sid": "another_sid",
            }

            def __init__(self):
                super().__init__()

        target = TestParentElementParser()

        target.populate(
            123,
            "900",
            "100",
            1,
            {
                "validity_start": "2023-01-01",
                "sid": "123",
                "language_id": "fghfgh",
                "update_type": 3,
                "update_type_name": "CREATE",
                "string_value": "happy",
                "float_value": "12.897",
            },
        )

        assert target.another_sid == 123
        assert target.validity_start == date(2023, 1, 1)

    def test_populate_errors_for_invalid_data_type(self):
        class TestParentElementParser(BaseTaricParser):
            xml_object_tag = "test.parent.element"

            record_code = "900"
            subrecord_code = "100"

            dict_value: dict = None

            def __init__(self):
                super().__init__()

        target = TestParentElementParser()

        e = None
        with pytest.raises(Exception) as e:
            target.populate(
                123,
                "900",
                "100",
                1,
                {
                    "dict_value": '{"fghfghfghfgh": "dfgdfgdfg"}',
                },
            )

        assert (
            "data type dict not handled, does the handler have the correct data type?"
            in str(e)
        )

    def test_populate_correctly_makes_valid_between_with_upper_and_lower(self):
        class TestParentElementParser(BaseTaricParser):
            xml_object_tag = "test.parent.element"

            record_code = "900"
            subrecord_code = "100"
            valid_between = None
            valid_between_lower: date = None
            valid_between_upper: date = None

            dict_value: dict = None

            def __init__(self):
                super().__init__()

        target = TestParentElementParser()

        target.populate(
            123,
            "900",
            "100",
            1,
            {
                "valid_between_lower": "2023-01-01",
                "valid_between_upper": "2023-12-31",
            },
        )

        assert target.valid_between == TaricDateRange(
            date(2023, 1, 1),
            date(2023, 12, 31),
        )
        assert target.valid_between_lower == date(2023, 1, 1)
        assert target.valid_between_upper == date(2023, 12, 31)

    def test_populate_correctly_makes_valid_between_with_just_lower(self):
        class TestParentElementParser(BaseTaricParser):
            xml_object_tag = "test.parent.element"

            record_code = "900"
            subrecord_code = "100"
            valid_between = None
            valid_between_lower: date = None
            valid_between_upper: date = None

            dict_value: dict = None

            def __init__(self):
                super().__init__()

        target = TestParentElementParser()

        target.populate(
            123,
            "900",
            "100",
            1,
            {
                "valid_between_lower": "2023-01-01",
            },
        )

        assert target.valid_between == TaricDateRange(date(2023, 1, 1))
        assert target.valid_between_lower == date(2023, 1, 1)
        assert target.valid_between_upper is None

    def test_to_tap_model(self):
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
            model = MadeUpModel

            model_links = []

            def __init__(self):
                super().__init__()

        parser = TestParentElementParser()

        parser.populate(
            123,
            "900",
            "100",
            1,
            {
                "valid_between_lower": "2023-01-01",
            },
        )

        transaction = factories.ApprovedTransactionFactory.create()

        target = parser.model_attributes(transaction)

        assert target["valid_between"] == TaricDateRange(date(2023, 1, 1))

    def test_to_tap_model_invalid_peoperty(self):
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

            model_links = []

            def __init__(self):
                super().__init__()

        parser = TestParentElementParser()

        parser.populate(
            123,
            "900",
            "100",
            1,
            {
                "valid_between_lower": "2023-01-01",
                "invalid_property": "dfgdfgdfg",
            },
        )

        transaction = factories.ApprovedTransactionFactory.create()

        e = None
        with pytest.raises(Exception) as e:
            parser.model_attributes(transaction)

        assert (
            "Error creating model MadeUpModel, model does not have an attribute invalid_property"
            in str(e)
        )

    def test_model_attributes_returns_expected(self, mocker):
        add_code_type = factories.AdditionalCodeTypeFactory.create(sid="A")

        class MadeUpModel:
            sequence_number: int = None
            transaction_id: int = None
            valid_between: TaricDateRange = None
            field_1: str = None
            another_field: int = None
            related_model: List[str] = None
            additional_code_type = AdditionalCodeType

            def __init__(self, **kwargs):
                for key, value in kwargs.items():
                    setattr(self, key, value)

        class TestParentElementParser(BaseTaricParser):
            xml_object_tag = "test.parent.element"

            record_code = "900"
            subrecord_code = "100"
            field_1: str = None
            another_field: str = None
            model = MadeUpModel
            additional_code_type__sid: str = None

            model_links = [
                ModelLink(
                    AdditionalCodeType,
                    [
                        ModelLinkField("additional_code_type__sid", "sid"),
                    ],
                    "additional.code.type",
                ),
            ]

            def __init__(self):
                super().__init__()

        appr_transaction = factories.ApprovedTransactionFactory.create()

        parser = TestParentElementParser()
        parser.populate(
            1,
            "900",
            "100",
            1,
            {
                "field_1": "aaa",
                "another_field": "123",
                "additional_code_type__sid": "A",
            },
        )

        # child_parser
        target = parser.model_attributes(appr_transaction)
        assert "field_1" in target.keys()
        assert "another_field" in target.keys()
        assert "additional_code_type" in target.keys()
        assert len(target.keys()) == 3
