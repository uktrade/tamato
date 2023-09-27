from datetime import date

import pytest

# note : need to import these objects to make them available to the parser
from commodities.models import GoodsNomenclature
from commodities.models import GoodsNomenclatureDescription
from commodities.new_import_parsers import NewGoodsNomenclatureDescriptionParser
from common.tests import factories
from common.tests.util import get_test_xml_file
from importer import new_importer
from workbaskets.models import WorkBasket
from workbaskets.validators import WorkflowStatus

pytestmark = pytest.mark.django_db


@pytest.mark.new_importer
class TestNewGoodsNomenclatureDescriptionParser:
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

    target_parser_class = NewGoodsNomenclatureDescriptionParser

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
        file_to_import = get_test_xml_file(
            "goods_nomenclature_description_with_period_CREATE.xml",
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

    def test_import_failure_no_period(self, superuser):
        file_to_import = get_test_xml_file(
            "goods_nomenclature_description_no_period_CREATE.xml",
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
            "Missing expected child object NewGoodsNomenclatureDescriptionPeriodParser"
            in str(importer.issues()[0])
        )
        assert (
            "goods.nomenclature.description > goods.nomenclature.description.period"
            in str(importer.issues()[0])
        )

    def test_import_successfully_gets_previous_period(self, superuser):
        file_to_import = get_test_xml_file(
            "goods_nomenclature_description_with_period_CREATE.xml",
            __file__,
        )

        workbasket = factories.WorkBasketFactory.create(status=WorkflowStatus.EDITING)
        import_batch = factories.ImportBatchFactory.create(workbasket=workbasket)
        user = factories.UserFactory.create()

        importer = new_importer.NewImporter(
            import_batch=import_batch,
            taric3_file=file_to_import,
            import_title="Importing stuff",
            author_username=superuser.username,
        )

        assert importer.can_save()
        assert len(importer.issues()) == 0

        # force publish workbasket
        workbasket = WorkBasket.objects.last()
        workbasket.full_clean()
        workbasket.approve(user.username, "REVISION_ONLY")
        workbasket.status = WorkflowStatus.QUEUED

        assert workbasket.status == WorkflowStatus.QUEUED

        # Now import an update to the description only
        file_to_import = get_test_xml_file(
            "goods_nomenclature_description_no_period_UPDATE.xml",
            __file__,
        )

        workbasket = factories.WorkBasketFactory.create(status=WorkflowStatus.EDITING)
        import_batch = factories.ImportBatchFactory.create(workbasket=workbasket)

        importer = new_importer.NewImporter(
            import_batch=import_batch,
            taric3_file=file_to_import,
            import_title="Importing more stuff",
            author_username=superuser.username,
        )

        assert len(importer.parsed_transactions) == 1

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
