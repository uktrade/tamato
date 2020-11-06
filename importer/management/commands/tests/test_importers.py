import os
import tempfile
from contextlib import contextmanager

import pytest
from django.core.management import call_command
from django.test import override_settings
from xmldiff import main

from common.tests import factories
from common.validators import ApplicabilityCode
from importer.management.commands.tests.test_utils import make_child

pytestmark = pytest.mark.django_db

fixture_path = "./importer/management/commands/tests/fixtures/"


@contextmanager
def output():
    temp = tempfile.NamedTemporaryFile(delete=False)
    try:
        yield temp
    finally:
        os.unlink(temp.name)


class TestTradeRemedies:
    def setup(self):
        # Add user
        factories.UserFactory.create(username="Alice")

        # Setup duty parsing
        factories.DutyExpressionFactory.create(
            sid=1,
            prefix="",
            duty_amount_applicability_code=ApplicabilityCode.MANDATORY,
            measurement_unit_applicability_code=ApplicabilityCode.PERMITTED,
            monetary_unit_applicability_code=ApplicabilityCode.PERMITTED,
        )
        factories.DutyExpressionFactory.create(
            sid=37,
            prefix="",
            duty_amount_applicability_code=ApplicabilityCode.NOT_PERMITTED,
            measurement_unit_applicability_code=ApplicabilityCode.NOT_PERMITTED,
            monetary_unit_applicability_code=ApplicabilityCode.NOT_PERMITTED,
        )
        factories.MonetaryUnitFactory.create(code="EUR")
        factories.MonetaryUnitFactory.create(code="GBP")
        tonne = factories.MeasurementUnitFactory.create(
            code="TNE",
            abbreviation="1,000 kg",
        )
        qualifier = factories.MeasurementUnitQualifierFactory.create(
            code="I",
            abbreviation="of biodiesel content",
        )
        factories.MeasurementFactory.create(
            measurement_unit=tonne,
            measurement_unit_qualifier=qualifier,
        )

        # Setup measures
        factories.MeasureTypeFactory.create(sid=552)
        factories.MeasureTypeFactory.create(sid=554)
        factories.MeasureConditionCodeFactory.create(code="A")
        factories.MeasureActionFactory.create(code="01")

        # Setup regulations
        regulation_group = factories.RegulationGroupFactory.create(
            group_id="DUM", description="Anti-dumping duties, countervailing duties"
        )
        factories.RegulationFactory(
            regulation_group=regulation_group, regulation_id="R0100010"
        )
        factories.RegulationFactory(
            regulation_group=regulation_group, regulation_id="R0200010"
        )
        factories.RegulationFactory(
            regulation_group=regulation_group, regulation_id="R0100030"
        )
        factories.RegulationFactory(
            regulation_group=regulation_group, regulation_id="R0100020"
        )

        # Setup certificates
        certificate_type = factories.CertificateTypeFactory.create(sid="D")
        factories.CertificateFactory.create(
            sid="008", certificate_type=certificate_type
        )

        # Setup good nomenclature
        root_cc = factories.GoodsNomenclatureFactory.create(
            sid="1",
            item_id="1000000000",
            suffix="80",
        )
        make_child(root_cc, sid="11", item_id="1100000000", suffix="80")
        make_child(root_cc, sid="12", item_id="1200000000", suffix="80")
        factories.GoodsNomenclatureFactory.create(
            sid="2",
            item_id="2000000000",
            suffix="80",
        )

        # Setup additional codes
        additional_code_type = factories.AdditionalCodeTypeFactory(
            sid="C",
            description="Anti-dumping/countervailing",
        )
        factories.AdditionalCodeFactory(
            sid="13160", code=555, type=additional_code_type
        )

        # Setup geographical area's
        area1 = factories.GeographicalAreaFactory.create(
            sid=103, area_id="US", area_code=0
        )
        area2 = factories.GeographicalAreaFactory.create(
            sid=140, area_id="AD", area_code=0
        )
        factories.GeographicalAreaDescriptionFactory.create(
            area=area1, description="United States of America"
        )
        factories.GeographicalAreaDescriptionFactory.create(
            area=area2, description="Andorra"
        )

        # Footnotes
        ftn = factories.FootnoteTypeFactory.create(footnote_type_id="FN")
        factories.FootnoteFactory.create(footnote_id="001", footnote_type=ftn)
        factories.FootnoteFactory.create(footnote_id="002", footnote_type=ftn)
        factories.FootnoteFactory.create(footnote_id="003", footnote_type=ftn)
        factories.FootnoteFactory.create(footnote_id="004", footnote_type=ftn)

    @override_settings(DATA_IMPORT_USERNAME="Alice")
    def test_import_trade_remedies(self):
        """
        Expected output:
        -  add regulation C2100005 for "DUM" (Anti-dumping duties, countervailing duties) group from 01/01/21
        -  ending of measure 1 for CC 1000000000 on 31/12/20
        -  ending of measure 2 for CC 1100000000 on 31/12/20
        -  ending of measure 3 for CC 1200000000 on 31/12/20
        -  ending of measure 4 for CC 1200000000 with additional code C555 on 31/12/20
        -  ending of measure 5 for CC 2000000000 on 31/12/20
        -  create measure 6 for CC 1200000000 on 01/01/21
            - footnotes FN001/FN002/FN004
            - measure component 120.5 / GBP / TNE / I (conversion of 144.000 * 0.83687 rounded down to nearest pence)
        -  create measure 7 for CC 1200000000 with additional code C555 on 01/01/21
            - footnotes FN004
            - measure component: measure side: 7 / duty amount: 20
        -  create measure 8 for CC 2000000000 on 01/01/21
            - measure condition sid 1:  measure sid: 8 / action code: 01 / condition code: A / cert type code: D /
                cert code: 008
            - measure condition component: measure condition sid: 1 / duty expression id: 01 /
                duty amount: 181.430 (converted) / monetary unit code: GBP /  measurement unit code: TNE /
                measurement unit qualitfier: I
            - measure condition sid 2:  measure sid: 8 / action code: 01/ condition code: A
            - measure condition component: measure condition sid: 2 / duty expression id: 37
        - 1100000000 not created as maintain is No
        - 1000000000 not created as overlapping with child 1200000000

        Total transactions: 5 ending and 3 create and 1 regulation = 9

        """
        args = [
            fixture_path + "trade_remedies/regulations_to_maintain.xlsx",
            fixture_path + "trade_remedies/existing_measures.xlsx",
        ]
        with output() as xml_output:
            opts = {
                "new_skip_rows": 1,
                "old_skip_rows": 1,
                "measure_sid": 6,
                "measure_condition_sid": 1,
                "transaction_id": 1,
                "envelope_id": 1,
                "output": xml_output.name,
            }
            call_command("import_trade_remedies", *args, **opts)
            expected_xml_output = fixture_path + "trade_remedies/expected_output.xml"
            diff = main.diff_files(
                xml_output,
                expected_xml_output,
            )
            assert not diff, f"Unexpected output: {diff}"


class TestImportTradeDisputes:
    def setup(self):
        # Add user
        factories.UserFactory.create(username="Alice")

        # Setup duty parsing
        factories.DutyExpressionFactory.create(
            sid=1,
            prefix="",
            duty_amount_applicability_code=ApplicabilityCode.MANDATORY,
            measurement_unit_applicability_code=ApplicabilityCode.PERMITTED,
            monetary_unit_applicability_code=ApplicabilityCode.PERMITTED,
        )
        factories.MonetaryUnitFactory.create(code="EUR")

        # Setup measures
        factories.MeasureTypeFactory.create(sid=695)
        factories.MeasureConditionCodeFactory.create(code="B")
        factories.MeasureActionFactory.create(code="27")
        factories.MeasureActionFactory.create(code="08")

        # Setup regulations
        regulation_group = factories.RegulationGroupFactory.create(
            group_id="ADD", description="Additional Duties (AGRI)"
        )
        factories.RegulationFactory(
            regulation_group=regulation_group, regulation_id="R0000001"
        )
        factories.RegulationFactory(
            regulation_group=regulation_group, regulation_id="R0000002"
        )

        # Setup certificates
        certificate_type = factories.CertificateTypeFactory.create(sid="N")
        factories.CertificateFactory.create(
            sid="990", certificate_type=certificate_type
        )

        # Setup good nomenclature
        root_cc = factories.GoodsNomenclatureFactory.create(
            sid="1",
            item_id="1000000000",
            suffix="80",
        )
        make_child(root_cc, sid="11", item_id="1100000000", suffix="80")
        make_child(root_cc, sid="12", item_id="1200000000", suffix="80")
        factories.GoodsNomenclatureFactory.create(
            sid="39",
            item_id="3900000000",
            suffix="80",
        )

        # Setup geographical area's
        area = factories.GeographicalAreaFactory.create(
            sid=103, area_id="US", area_code=0
        )
        factories.GeographicalAreaDescriptionFactory.create(
            area=area, description="United States of America"
        )

        # Footnotes
        ftn = factories.FootnoteTypeFactory.create(footnote_type_id="FN")
        factories.FootnoteFactory.create(footnote_id="001", footnote_type=ftn)
        factories.FootnoteFactory.create(footnote_id="002", footnote_type=ftn)
        factories.FootnoteFactory.create(footnote_id="003", footnote_type=ftn)
        factories.FootnoteFactory.create(footnote_id="004", footnote_type=ftn)

    @override_settings(DATA_IMPORT_USERNAME="Alice")
    def test_import_trade_disputes(self):
        """
        Preconditions:
        - existing_measures and new_measures input files are sorted with ascending
            commodity code
        - both files have like for like measures regarding same country etc?

        Expected output:
        - add regulation C2100004 for "ADD" (Additional duties) group from 01/01/21
        - ending of measure 2 for CC 1100000000 on 31/12/20
        - ending of measure 1 for CC 1000000000 on 31/12/20
        - ending of measure 3 for CC 1200000000 on 31/12/20
        - restart of measure (4 for CC 1100000000 on 01/01/21
            - footnote FN003
            - duty amount 30
        - restart of measure 5 for CC 1200000000 on 01/01/21
            - footnote FN001, FN002, FN004?
            - duty amount 25
        - new measure 6 for CC 3900000000 on 01/01/21
            - duty amount 1
        """
        args = [
            fixture_path + "trade_disputes/new_measures.xlsx",
            fixture_path + "trade_disputes/existing_measures.xlsx",
        ]
        with output() as xml_output:
            opts = {
                "new_skip_rows": 3,
                "old_skip_rows": 1,
                "measure_sid": 4,
                "measure_condition_sid": 1,
                "transaction_id": 1,
                "output": xml_output.name,
            }
            call_command("import_trade_disputes", *args, **opts)
            expected_xml_output = fixture_path + "trade_disputes/expected_output.xml"
            diff = main.diff_files(
                xml_output,
                expected_xml_output,
            )
            assert not diff, f"Unexpected output: {diff}"


class TestImportCountries:
    @override_settings(DATA_IMPORT_USERNAME="Alice")
    def test_update_area_description(self):
        """
        Expected output:
        - description for geographical area with sid 1 changed to Andorra

        """
        factories.UserFactory.create(username="Alice")
        geo_area = factories.GeographicalAreaFactory.create(
            sid=1,
            area_id="AD",
            area_code=0,
        )
        factories.GeographicalAreaDescriptionFactory.create(
            sid=1,
            area=geo_area,
            description="old description",
        )
        args = [
            fixture_path + "countries/countries-territories-and-regions.xlsx",
            "Sheet1",
        ]
        with output() as xml_output:
            opts = {"skip_rows": 1, "transaction_id": 1, "output": xml_output.name}
            call_command("import_countries", *args, **opts)
            expected_xml_output = fixture_path + "countries/expected_output.xml"
            diff = main.diff_files(
                xml_output,
                expected_xml_output,
            )
            assert not diff, f"Unexpected output: {diff}"
            # assert geo_description.description == 'Andorra'
