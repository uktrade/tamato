from datetime import date

import pytest

# note : need to import these objects to make them available to the parser
from commodities.models import GoodsNomenclatureDescription
from commodities.new_import_parsers import NewGoodsNomenclatureDescriptionPeriodParser
from common.tests import factories
from common.tests.util import get_test_xml_file
from importer import new_importer
from workbaskets.validators import WorkflowStatus

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

    def test_import(self, superuser):
        file_to_import = get_test_xml_file(
            "goods_nomenclature_description_period_UPDATE.xml",
            __file__,
        )

        workbasket = factories.WorkBasketFactory.create(status=WorkflowStatus.EDITING)
        import_batch = factories.ImportBatchFactory.create(workbasket=workbasket)

        importer = new_importer.NewImporter(
            import_batch=import_batch,
            taric3_file=file_to_import,
            import_title="Importing stuff",
            author_username=superuser.username,
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
