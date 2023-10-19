from datetime import date

import pytest

# note : need to import these objects to make them available to the parser
from commodities.models import GoodsNomenclatureDescription
from common.tests.util import preload_import
from taric_parsers.parsers.commodity_parser import *

pytestmark = pytest.mark.django_db


@pytest.mark.new_importer
class TestNewGoodsNomenclatureDescriptionPeriodParser:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="goods.nomenclature.description.period" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="goods.nomenclature.description.period.sid" type="SID"/>
                    <xs:element name="goods.nomenclature.sid" type="SID"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="goods.nomenclature.item.id" type="GoodsNomenclatureItemId"/>
                    <xs:element name="productline.suffix" type="ProductLineSuffix"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    target_parser_class = NewGoodsNomenclatureDescriptionPeriodParser

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "goods_nomenclature_description_period_sid": "7",
            "goods_nomenclature_sid": "555",
            "goods_nomenclature_item_id": "0100000000",
            "language_id": "ZZ",
            "productline_suffix": "10",
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
        assert target.sid == 7
        assert target.described_goods_nomenclature__sid == 555
        assert target.described_goods_nomenclature__item_id == "0100000000"
        assert target.described_goods_nomenclature__suffix == 10

    def test_import_create_and_update_in_same_file(self, superuser):
        importer = preload_import(
            "goods_nomenclature_description_period_UPDATE.xml",
            __file__,
        )

        assert len(importer.parsed_transactions) == 3

        target_message = importer.parsed_transactions[2].parsed_messages[0]

        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        # check properties
        target = target_message.taric_object

        assert target.sid == 7
        assert target.described_goods_nomenclature__sid == 1
        assert target.described_goods_nomenclature__item_id == "0100000000"
        assert target.described_goods_nomenclature__suffix == 10

        assert len(importer.issues()) == 0

        assert GoodsNomenclatureDescription.objects.all().count() == 2
        assert GoodsNomenclatureDescription.objects.all().last().validity_start == date(
            2021,
            1,
            2,
        )

    def test_import_update(self, superuser):
        preload_import(
            "goods_nomenclature_description_period_UPDATE.xml",
            __file__,
            True,
        )
        importer = preload_import(
            "goods_nomenclature_description_period_only_UPDATE.xml",
            __file__,
        )

        target_message = importer.parsed_transactions[0].parsed_messages[0]

        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        # check properties
        target = target_message.taric_object

        assert target.sid == 7
        assert target.described_goods_nomenclature__sid == 1
        assert target.described_goods_nomenclature__item_id == "0100000000"
        assert target.described_goods_nomenclature__suffix == 10

        assert len(importer.issues()) == 0

        assert GoodsNomenclatureDescription.objects.all().count() == 3
        assert GoodsNomenclatureDescription.objects.all().last().validity_start == date(
            2021,
            1,
            3,
        )

    def test_import_delete(self, superuser):
        preload_import(
            "goods_nomenclature_description_period_UPDATE.xml",
            __file__,
            True,
        )
        importer = preload_import(
            "goods_nomenclature_description_period_only_DELETE.xml",
            __file__,
        )

        assert not importer.can_save()
        assert len(importer.issues()) == 1
        assert (
            "Children of Taric objects of type GoodsNomenclatureDescription can't be deleted directly"
            in str(importer.issues()[0])
        )
