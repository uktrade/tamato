from datetime import date

import pytest

# note : need to import these objects to make them available to the parser
from commodities.models import GoodsNomenclature
from commodities.models import GoodsNomenclatureDescription
from common.tests.util import preload_import
from taric_parsers.parsers.commodity_parser import *

pytestmark = pytest.mark.django_db


@pytest.mark.importer_v2
class TestGoodsNomenclatureDescriptionParserV2:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="goods.nomenclature.description" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="goods.nomenclature.description.period.sid" type="SID"/>
                    <xs:element name="goods.nomenclature.sid" type="SID"/>
                    <xs:element name="goods.nomenclature.item.id" type="GoodsNomenclatureItemId"/>
                    <xs:element name="language.id" type="LanguageId"/>
                    <xs:element name="productline.suffix" type="ProductLineSuffix"/>
                    <xs:element name="description" type="LongDescription" minOccurs="0"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    target_parser_class = GoodsNomenclatureDescriptionParserV2

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "goods_nomenclature_description_period_sid": "7",
            "goods_nomenclature_sid": "555",
            "goods_nomenclature_item_id": "0100000000",
            "language_id": "ZZ",
            "productline_suffix": "10",
            "description": "Some Description",
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
        assert target.description == "Some Description"

    def test_import(self, superuser):
        importer = preload_import(
            "goods_nomenclature_description_with_period_CREATE.xml",
            __file__,
        )

        assert len(importer.parsed_transactions) == 2
        assert len(importer.parsed_transactions[1].parsed_messages) == 2

        target_message = importer.parsed_transactions[1].parsed_messages[0]

        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        target = target_message.taric_object

        assert target.sid == 7
        assert target.described_goods_nomenclature__sid == 1
        assert target.described_goods_nomenclature__item_id == "0100000000"
        assert target.description == "Some Description"
        assert target.described_goods_nomenclature__suffix == 10

        assert GoodsNomenclatureDescription.objects.all().count() == 1
        assert GoodsNomenclature.objects.all().count() == 1

        assert len(importer.issues()) == 0

    def test_import_update(self, superuser):
        preload_import(
            "goods_nomenclature_description_with_period_CREATE.xml",
            __file__,
            True,
        )
        importer = preload_import("goods_nomenclature_description_UPDATE.xml", __file__)

        target_message = importer.parsed_transactions[0].parsed_messages[0]
        target = target_message.taric_object

        assert target.sid == 7
        assert target.described_goods_nomenclature__sid == 1
        assert target.described_goods_nomenclature__item_id == "0100000000"
        assert target.description == "Some Description that changed"
        assert target.described_goods_nomenclature__suffix == 10

        assert GoodsNomenclatureDescription.objects.all().count() == 2
        assert GoodsNomenclature.objects.all().count() == 1

        assert len(importer.issues()) == 0

    def test_import_delete(self, superuser):
        preload_import(
            "goods_nomenclature_description_with_period_CREATE.xml",
            __file__,
            True,
        )
        importer = preload_import("goods_nomenclature_description_DELETE.xml", __file__)

        assert importer.can_save()
        assert GoodsNomenclatureDescription.objects.all().count() == 2
        assert len(importer.issues()) == 0

    def test_import_failure_no_period(self, superuser):
        importer = preload_import(
            "goods_nomenclature_description_no_period_CREATE.xml",
            __file__,
        )

        assert not importer.can_save()

        assert len(importer.parsed_transactions) == 2
        assert len(importer.parsed_transactions[1].parsed_messages) == 1

        target_message = importer.parsed_transactions[1].parsed_messages[0]

        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        target = target_message.taric_object

        assert target.sid == 9
        assert target.described_goods_nomenclature__sid == 7
        assert target.described_goods_nomenclature__item_id == "0102000000"
        assert target.description == "Some Description"
        assert target.described_goods_nomenclature__suffix == 10

        assert (
            len(importer.parsed_transactions[1].parsed_messages[0].taric_object.issues)
            == 1
        )

        assert len(importer.issues()) == 1
        assert (
            "Missing expected child object GoodsNomenclatureDescriptionPeriodParserV2"
            in str(importer.issues()[0])
        )
        assert (
            "goods.nomenclature.description > goods.nomenclature.description.period"
            in str(importer.issues()[0])
        )

    def test_import_successfully_gets_previous_period(self, superuser):
        # preload data and approve
        preload_import(
            "goods_nomenclature_description_with_period_CREATE.xml",
            __file__,
            True,
        )

        # load data not approved
        importer = preload_import(
            "goods_nomenclature_description_no_period_UPDATE.xml",
            __file__,
        )

        assert len(importer.parsed_transactions) == 1

        assert importer.issues() == []

        assert importer.can_save()

        target_message = importer.parsed_transactions[0].parsed_messages[0]

        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        target = target_message.taric_object

        assert target.sid == 7
        assert target.described_goods_nomenclature__sid == 1
        assert target.described_goods_nomenclature__item_id == "0100000000"
        assert target.description == "Some Description Changed"
        assert target.described_goods_nomenclature__suffix == 10

        assert len(importer.issues()) == 0

        assert GoodsNomenclatureDescription.objects.all().count() == 2

        last_imported_goods_description = (
            GoodsNomenclatureDescription.objects.all().order_by("pk").last()
        )

        assert last_imported_goods_description.description == "Some Description Changed"
        assert last_imported_goods_description.sid == 7
        assert last_imported_goods_description.validity_start == date(2021, 1, 1)
