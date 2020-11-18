import os
import tempfile
from contextlib import contextmanager
from datetime import datetime
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.test import override_settings
from psycopg2._range import DateTimeTZRange
from xmldiff import main

from common.tests import factories
from common.validators import ApplicabilityCode
from importer.management.commands.patterns import LONDON
from importer.management.commands.tests.test_utils import make_child

pytestmark = pytest.mark.django_db

fixture_path = "./importer/management/commands/tests/fixtures/"


START_TIME = LONDON.localize(datetime(2019, 1, 1))


@contextmanager
def output():
    temp = tempfile.NamedTemporaryFile(delete=False)
    try:
        yield temp
    finally:
        os.unlink(temp.name)


class TestSteelSafeguards:

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
            valid_between=DateTimeTZRange(START_TIME, None)
        )

        # Setup measures
        series = factories.MeasureTypeSeriesFactory(valid_between=DateTimeTZRange(START_TIME, None))
        factories.MeasureTypeFactory.create(
            sid=696,
            valid_between=DateTimeTZRange(START_TIME, None),
            measure_type_series=series
        )
        factories.MeasureTypeFactory.create(
            sid=122,
            valid_between=DateTimeTZRange(START_TIME, None),
            measure_type_series=series
        )

        # Setup regulations
        factories.RegulationGroupFactory.create(
            group_id="KON",
            description="Non preferential tariff quotas",
            valid_between=DateTimeTZRange(START_TIME, None),
        )
        factories.RegulationGroupFactory.create(
            group_id="TXC",
            description="Countervailing charge",
            valid_between=DateTimeTZRange(START_TIME, None),
        )
        factories.RegulationFactory(
            approved=False,
            regulation_id="C0000001",
            valid_between=DateTimeTZRange(START_TIME, None),
        )

        # Setup good nomenclature
        factories.SimpleGoodsNomenclatureFactory.create(
            sid="1",
            item_id="1000000000",
            suffix="80",
            valid_between=DateTimeTZRange(START_TIME, None)
        )
        factories.SimpleGoodsNomenclatureFactory.create(
            sid="21",
            item_id="2100000000",
            suffix="80",
            valid_between=DateTimeTZRange(START_TIME, None)
        )
        factories.SimpleGoodsNomenclatureFactory.create(
            sid="22",
            item_id="2200000000",
            suffix="80",
            valid_between=DateTimeTZRange(START_TIME, None)
        )
        # Setup geographical area's
        factories.GeographicalAreaFactory.create(
            sid=494, area_id="5002", area_code=1, valid_between=DateTimeTZRange(START_TIME, None)
        )   # countries subject to safeguard measures
        factories.GeographicalAreaFactory.create(
            sid=169, area_id="EU", area_code=0, valid_between=DateTimeTZRange(START_TIME, None)
        )   # European Union
        factories.GeographicalAreaFactory.create(
            sid=439, area_id="CN", area_code=0, valid_between=DateTimeTZRange(START_TIME, None)
        )   # China
        factories.GeographicalAreaFactory.create(
            sid=94, area_id="BR", area_code=0, valid_between=DateTimeTZRange(START_TIME, None)
        )   # Brasil
        factories.GeographicalAreaFactory.create(
            sid=39, area_id="SA", area_code=0, valid_between=DateTimeTZRange(START_TIME, None)
        )   # Saudi Arabia
        factories.GeographicalAreaFactory.create(
            sid=98, area_id="TH", area_code=0, valid_between=DateTimeTZRange(START_TIME, None)
        )   # Thailand
        factories.GeographicalAreaFactory.create(
            sid=497, area_id="5051", area_code=1, valid_between=DateTimeTZRange(START_TIME, None)
        )   # countries subject to UK safeguard measures (large traders)
        factories.GeographicalAreaFactory.create(
            sid=496, area_id="5050", area_code=1, valid_between=DateTimeTZRange(START_TIME, None)
        )   # countries subject to UK safeguard measures
        # Setup measurements
        factories.MeasurementUnitFactory.create(
            code="KGM",
            abbreviation="kg",
            valid_between=DateTimeTZRange(START_TIME, None),
        )

    @override_settings(DATA_IMPORT_USERNAME="Alice")
    @patch.dict(
        'importer.management.commands.import_steel_safeguards.PRODUCT_CATEGORY_MAPPING',
        {
            '1': ['1000000000'],
            '2': ['2100000000', '2200000000'],
        },
        clear=True
    )
    @patch.dict(
        'importer.management.commands.import_steel_safeguards.OTHER_COUNTRIES_GROUP',
        {
            '5002_group': ['439', '98'],
            'extra_from_eu': ['169'],
            'potential_non_dev_exemptions_not_in_5002': ['94'],
            'new_dev_exemptions_and_trade_agreements': ['59'],
        },
        clear=True
    )
    @patch.dict(
        'importer.management.commands.import_steel_safeguards.LARGE_TRADER_GROUP',
        {
            'China': '439',
            'EU': '169',
        },
        clear=True
    )
    def test_import_steel_safeguards(self):
        """
        Expected output:

            SETUP REGULATION
            ----------------
            - transaction 1&2:
                - add regulation C2100007 for "KON" (Non preferential tariff quotas) group from 01/01/21
                - add regulation C2100008 for "TXC" (Countervailing charge) group from 01/01/21

            SETUP COUNTRY GROUPS
            --------------------
            - transaction 3&4:
                - group 5050 Other countries subject to UK safeguard measures
                - group 5051 Other countries subject to UK safeguard measures (large traders)

            MEASURE ENDINGS
            ---------------
            - transaction 5: ending of measure 1 for CC 1000000000 on 31/12/20

            CREATE NEW ADDITIONAL DUTIES
            ----------------------------

            - transaction 6 CC 1000000000:
                - measure 2
                    - validity between 01/01/21 and ...
                    - type: 696
                    - geo sid: 5050
                    - geo exemptions: BR (DEV exemption)
                    - measure component:
                        - duty amount: 25%

            - transaction 7 CC 2000000000:
                - measure 3
                    - validity between 01/01/21 and ...
                    - type: 696
                    - geo sid: 5050
                    - geo exemptions: SA (DEV exemption)
                    - measure component:
                        - duty amount: 25%

            CREATE NEW NON PREF DUTIES
            --------------------------

            category 1 - CC 1000000000

            - transaction 8&9:
                - quota order number 1: 100001
                    - validity between 01/01/21 and ...
                - quota origin 1:
                    - order number sid: 1
                    - validity between 01/01/21 and ...
                    - geo sid: 114 (EU)
                - measure 4
                    - validity between 01/01/21 and 30/06/21
                    - type: 122
                    - order number: 100001
                    - geo sid: 114 (EU)
                    - measure component:
                        - duty amount: 0%
            - transaction 10 & 11:
                - quota definition 1
                    - for order number: 100001
                    - validity between 01/01/21 and 31/03/21
                    - volume/initial volume: 100000000 kg
                - quota definition 2
                    - for order number: 100001
                    - validity between 01/04/21 and 30/06/21
            - transaction 12 & 13:
                - quota order number 2: 100002
                    - validity between 01/01/21 and ... (exclude Q4 for residual)
                - quota origin 2:
                    - order number sid: 2
                    - validity between 01/01/21 and ...
                    - geo sid: 494 (Other Countries)
                - quota origin exclusion
                    - order origin sid: 2
                    - geo sid: 94 (BR) (non-dev-exemption)
                    - geo sid: 114 (EU) (Large trader)
                - measure 5
                    - validity between 01/01/21 and 31/03/21 (exclude Q4)
                    - type: 122
                    - order number: 100002
                    - geo sid: 494 (Other Countries)
                    - exclude geo sid: 94 (BR) (non-dev-exemption)
                    - exclude geo sid: 114 (EU) (Large trader)
                    - measure component:
                        - duty amount: 0%
            - transaction 14:
                - quota definition 3
                    - for order number: 100002
                    - validity between 01/01/21 and 31/03/21
                    - volume/initial volume: 10000000.000 kg
            - transaction 15 & 16:
                - quota order number 3: 200002
                    - validity between 01/04/21 and ... (Q4)
                - quota origin 3:
                    - order number sid: 3
                    - validity between 01/04/21 and ...
                    - geo sid: 496 (Other Countries)
                - quota origin exclusion
                    - order origin sid: 3
                    - geo sid: 94 (BR) (non-dev-exemption), 169 EU (large trader)
                - measure 6:
                    - validity between 01/04/21 and 30/06/21 (Q4)
                    - type: 122
                    - order number: 100002
                    - geo sid: 496 (Other Countries)
                    - exclude geo sid: 94 (BR) (non-dev-exemption), 169 EU (large trader)
                    - measure component:
                        - duty amount: 0%
            - transaction 17:
                - quota definition 4
                    - for order number: 200002
                    - validity between 01/04/21 and 30/06/21
                    - volume/initial volume: 20000000.000 kg
            - transaction 18:
                - sub quota order 4: 300001
                    - validity between 01/04/21 and ...
                - sub quota origin 4:
                    - validity between 01/04/21 and ...
                    - geo sid: 114 (EU)
            - transaction 19:
                - sub quota definition 5:
                    - for order number: 300001
                    - validity between 01/04/21 and 30/06/21
                    - volume/initial volume: 14000000.000 (70% of 20M)
                - quota association:
                    - main quota def sid: 4
                    - sub quota def sid: 5
                    - type: NM
                    - coeff: 1.0000
            - transaction 20:
                - measure 7:
                    - validity between 01/04/21 and 30/06/21 (Q4)
                    - type: 122
                    - order number: 3001
                    - geo sid: 169 (EU)
                    - measure component:
                        - duty amount: 0%

            category 2 - CC 2000000000 (13 transactions)
                ...
        """
        args = [
            fixture_path + "steel_safeguards/new_measures.xlsx",
            fixture_path + "steel_safeguards/existing_measures.xlsx",
        ]
        with output() as xml_output:
            opts = {
                "old_skip_rows": 1,
                "measure_sid": 2,
                "measure_condition_sid": 1,
                "transaction_id": 1,
                "quota_order_number_sid": 1,
                "quota_order_number_origin_sid": 1,
                "quota_definition_sid": 1,
                "envelope_id": 1,
                "output": xml_output.name,
            }
            call_command("import_steel_safeguards", *args, **opts)
            expected_xml_output = fixture_path + "steel_safeguards/expected_output.xml"
            diff = main.diff_files(
                xml_output,
                expected_xml_output,
            )
            assert not diff, f"Unexpected output: {diff}"


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
            valid_between=DateTimeTZRange(START_TIME, None),
        )
        make_child(
            root_cc,
            sid="11",
            item_id="1100000000",
            suffix="80",
            valid_between=DateTimeTZRange(START_TIME, None)
        )
        make_child(
            root_cc, sid="12",
            item_id="1200000000",
            suffix="80",
            valid_between=DateTimeTZRange(START_TIME, None)
        )
        factories.GoodsNomenclatureFactory.create(
            sid="2",
            item_id="2000000000",
            suffix="80",
            valid_between=DateTimeTZRange(START_TIME, None),
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
        root_cc = factories.SimpleGoodsNomenclatureFactory.create(
            sid="1",
            item_id="1000000000",
            suffix="80",
        )
        make_child(root_cc, sid="11", item_id="1100000000", suffix="80")
        make_child(root_cc, sid="12", item_id="1200000000", suffix="80")
        factories.SimpleGoodsNomenclatureFactory.create(
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
