from datetime import date

import pytest

# note : need to import these objects to make them available to the parser
from commodities.models import GoodsNomenclature
from common.tests.util import preload_import
from taric_parsers.parsers.commodity_parser import *

pytestmark = pytest.mark.django_db


@pytest.mark.importer_v2
class TestGoodsNomenclatureParserV2:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="goods.nomenclature" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="goods.nomenclature.sid" type="SID"/>
                    <xs:element name="goods.nomenclature.item.id" type="GoodsNomenclatureItemId"/>
                    <xs:element name="producline.suffix" type="ProductLineSuffix"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                    <xs:element name="statistical.indicator" type="StatisticalIndicator"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    target_parser_class = GoodsNomenclatureParserV2

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "goods_nomenclature_sid": "555",
            "goods_nomenclature_item_id": "0100000000",  # gets ignored, but will come in from import
            "producline_suffix": "10",
            "validity_start_date": "2020-01-01",
            "validity_end_date": "2020-12-01",
            "statistical_indicator": "0",
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
        assert target.sid == 555
        assert target.item_id == "0100000000"
        assert target.suffix == 10
        assert target.valid_between_lower == date(2020, 1, 1)
        assert target.valid_between_upper == date(2020, 12, 1)
        assert target.statistical == 0

    def test_import(self, superuser):
        importer = preload_import("goods_nomenclature_CREATE.xml", __file__)

        assert len(importer.parsed_transactions) == 1
        assert len(importer.parsed_transactions[0].parsed_messages) == 1

        target_message = importer.parsed_transactions[0].parsed_messages[0]

        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        target_taric_object = target_message.taric_object
        assert target_taric_object.sid == 1
        assert target_taric_object.item_id == "0100000000"
        assert target_taric_object.suffix == 10
        assert target_taric_object.valid_between_lower == date(2021, 1, 1)
        assert target_taric_object.valid_between_upper is None
        assert target_taric_object.statistical == 0

        assert GoodsNomenclature.objects.all().count() == 1

        assert len(importer.issues()) == 0

    def test_import_then_delete(self, superuser):
        importer = preload_import("goods_nomenclature_CREATE_then_DELETE.xml", __file__)

        assert len(importer.parsed_transactions) == 2

        target_message = importer.parsed_transactions[0].parsed_messages[0]

        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        target_taric_object = target_message.taric_object
        assert target_taric_object.sid == 1
        assert target_taric_object.item_id == "0100000000"
        assert target_taric_object.suffix == 10
        assert target_taric_object.valid_between_lower == date(2021, 1, 1)
        assert target_taric_object.valid_between_upper is None
        assert target_taric_object.statistical == 0

        assert GoodsNomenclature.objects.all().count() == 2
        assert GoodsNomenclature.objects.latest_approved().count() == 0

        assert len(importer.issues()) == 0

    def test_import_update(self, superuser):
        preload_import("goods_nomenclature_CREATE.xml", __file__, True)
        importer = preload_import("goods_nomenclature_UPDATE.xml", __file__)

        target_message = importer.parsed_transactions[0].parsed_messages[0]

        target_taric_object = target_message.taric_object

        assert target_taric_object.sid == 1
        assert target_taric_object.item_id == "0100000000"
        assert target_taric_object.suffix == 10
        assert target_taric_object.valid_between_lower == date(2021, 1, 2)
        assert target_taric_object.valid_between_upper is None
        assert target_taric_object.statistical == 0

        assert GoodsNomenclature.objects.all().count() == 2
        assert GoodsNomenclature.objects.latest_approved().count() == 1

        assert len(importer.issues()) == 0

        latest_gn = GoodsNomenclature.objects.all().order_by("pk").last()

        assert latest_gn.valid_between.lower == date(2021, 1, 2)

    def test_import_delete_raises_issue(self, superuser):
        preload_import("goods_nomenclature_CREATE.xml", __file__, True)
        importer = preload_import("goods_nomenclature_DELETE.xml", __file__)

        assert len(importer.issues()) == 0
        assert importer.can_save()
        assert GoodsNomenclature.objects.all().count() == 2
        assert GoodsNomenclature.objects.latest_approved().count() == 1
