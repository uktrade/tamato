from datetime import date

import pytest

# note : need to import these objects to make them available to the parser
from commodities.models import FootnoteAssociationGoodsNomenclature
from commodities.models import GoodsNomenclature
from common.tests.util import preload_import
from taric_parsers.parsers.commodity_parser import *
from taric_parsers.parsers.footnote_parser import *

pytestmark = pytest.mark.django_db


@pytest.mark.importer_v2
class TestNewFootnoteAssociationGoodsNomenclatureParser:
    """
    Example XML:

    .. code-block:: XML

        <xs:element name="footnote.association.goods.nomenclature" substitutionGroup="abstract.record">
            <xs:complexType>
                <xs:sequence>
                    <xs:element name="goods.nomenclature.sid" type="SID"/>
                    <xs:element name="footnote.type" type="FootnoteTypeId"/>
                    <xs:element name="footnote.id" type="FootnoteId"/>
                    <xs:element name="validity.start.date" type="Date"/>
                    <xs:element name="validity.end.date" type="Date" minOccurs="0"/>
                    <xs:element name="goods.nomenclature.item.id" type="GoodsNomenclatureItemId"/>
                    <xs:element name="productline.suffix" type="ProductLineSuffix"/>
                </xs:sequence>
            </xs:complexType>
        </xs:element>
    """

    target_parser_class = NewFootnoteAssociationGoodsNomenclatureParser

    def test_it_handles_population_from_expected_data_structure(self):
        expected_data_example = {
            "goods_nomenclature_sid": "8",
            "footnote_type": "8",
            "footnote_id": "8",
            "validity_start_date": "2022-01-01",
            "validity_end_date": "2023-01-01",
            "goods_nomenclature_item_id": "0100000000",
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

        assert target.goods_nomenclature__sid == 8
        assert target.associated_footnote__footnote_type__footnote_type_id == 8
        assert target.associated_footnote__footnote_id == 8
        assert target.valid_between_lower == date(2022, 1, 1)
        assert target.valid_between_upper == date(2023, 1, 1)
        assert target.goods_nomenclature__item_id == "0100000000"
        assert target.goods_nomenclature__suffix == 10

    def test_import(self, superuser):
        importer = preload_import(
            "footnote_association_goods_nomenclature_CREATE.xml",
            __file__,
        )

        assert len(importer.parsed_transactions) == 2
        assert len(importer.parsed_transactions[0].parsed_messages) == 4
        assert len(importer.parsed_transactions[1].parsed_messages) == 1

        target_message = importer.parsed_transactions[1].parsed_messages[0]

        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        target = target_message.taric_object

        assert target.goods_nomenclature__sid == 1
        assert target.associated_footnote__footnote_type__footnote_type_id == 3
        assert target.associated_footnote__footnote_id == 9
        assert target.valid_between_lower == date(2022, 1, 1)
        assert target.valid_between_upper == date(2023, 1, 1)
        assert target.goods_nomenclature__item_id == "0100000000"
        assert target.goods_nomenclature__suffix == 10

        assert FootnoteAssociationGoodsNomenclature.objects.all().count() == 1
        assert GoodsNomenclature.objects.all().count() == 1

        assert len(importer.issues()) == 0

    def test_import_update(self):
        preload_import(
            "footnote_association_goods_nomenclature_CREATE.xml",
            __file__,
            True,
        )
        importer = preload_import(
            "footnote_association_goods_nomenclature_UPDATE.xml",
            __file__,
        )

        target_message = importer.parsed_transactions[0].parsed_messages[0]
        target = target_message.taric_object

        assert target.goods_nomenclature__sid == 1
        assert target.associated_footnote__footnote_type__footnote_type_id == 3
        assert target.associated_footnote__footnote_id == 9
        assert target.valid_between_lower == date(2022, 1, 11)
        assert target.valid_between_upper == date(2023, 1, 1)
        assert target.goods_nomenclature__item_id == "0100000000"
        assert target.goods_nomenclature__suffix == 10

        assert FootnoteAssociationGoodsNomenclature.objects.all().count() == 2

        assert len(importer.issues()) == 0

    def test_import_delete(self):
        preload_import(
            "footnote_association_goods_nomenclature_CREATE.xml",
            __file__,
            True,
        )
        importer = preload_import(
            "footnote_association_goods_nomenclature_DELETE.xml",
            __file__,
        )

        assert len(importer.issues()) == 0
        assert importer.can_save()

        assert FootnoteAssociationGoodsNomenclature.objects.all().count() == 2

    def test_import_failure_no_footnote(self, superuser):
        importer = preload_import(
            "footnote_association_goods_nomenclature_no_footnote_CREATE.xml",
            __file__,
        )

        assert not importer.can_save()

        assert len(importer.parsed_transactions) == 2
        assert len(importer.parsed_transactions[1].parsed_messages) == 1

        target_message = importer.parsed_transactions[1].parsed_messages[0]

        assert target_message.record_code == self.target_parser_class.record_code
        assert target_message.subrecord_code == self.target_parser_class.subrecord_code
        assert type(target_message.taric_object) == self.target_parser_class

        assert len(importer.issues()) == 2
        assert "ERROR: Missing expected linked object NewFootnoteParser\n" in str(
            importer.issues()[0],
        )
        assert (
            "ERROR: Database Integrity error, review related issues to determine what went wrong null value in column "
            '"associated_footnote_id" of relation "commodities_footnoteassociationgoodsnomenclature" violates not-null '
            "constraint\n" in str(importer.issues()[1])
        )
