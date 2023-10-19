import pytest

# note : need to import these objects to make them available to the parser
from common.tests.util import preload_import
from measures.models import MonetaryUnit
from taric_parsers.parsers.geo_area_parser import *
from taric_parsers.parsers.measure_parser import *

pytestmark = pytest.mark.django_db


@pytest.mark.new_importer
class TestNewMonetaryUnitParser:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="monetary.unit" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="monetary.unit.code" type="MonetaryUnitCode"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    target_parser_class = NewMonetaryUnitParser

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "monetary_unit_code": "ZZZ",
            "validity_start_date": "2021-01-01",
            "validity_end_date": "2022-01-01",
        }

        target = self.target_parser_class()

        target.populate(
            1,  # transaction id
            target.record_code,
            target.subrecord_code,
            1,  # sequence number
            expected_data_example,
        )

        # verify all properties
        assert target.code == "ZZZ"
        assert target.valid_between_lower == date(2021, 1, 1)
        assert target.valid_between_upper == date(2022, 1, 1)

    def test_import(self, superuser):
        importer = preload_import("monetary_unit_CREATE.xml", __file__)

        assert len(importer.parsed_transactions) == 1

        target_message = importer.parsed_transactions[0].parsed_messages[0]
        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        target = target_message.taric_object

        assert target.code == "ZZZ"
        assert target.valid_between_lower == date(2021, 1, 1)
        assert target.valid_between_upper == date(2022, 1, 1)

        assert len(importer.issues()) == 0

        assert MonetaryUnit.objects.all().count() == 1

    def test_import_update(self, superuser):
        preload_import("monetary_unit_CREATE.xml", __file__, True)
        importer = preload_import("monetary_unit_UPDATE.xml", __file__)

        target_message = importer.parsed_transactions[0].parsed_messages[0]

        target = target_message.taric_object

        assert target.code == "ZZZ"
        assert target.valid_between_lower == date(2021, 1, 11)
        assert target.valid_between_upper == date(2022, 1, 1)

        assert len(importer.issues()) == 0

        assert MonetaryUnit.objects.all().count() == 2
