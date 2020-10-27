import os
import tempfile
from contextlib import contextmanager

import pytest
from django.core.management import call_command
from django.test import override_settings

from common.validators import ApplicabilityCode
from common.tests import factories
from xmldiff import main

from importer.management.commands.tests.test_utils import make_child

pytestmark = pytest.mark.django_db

fixture_path = './importer/management/commands/tests/fixtures/'


@contextmanager
def output():
    temp = tempfile.NamedTemporaryFile(delete=False)
    try:
        yield temp
    finally:
        os.unlink(temp.name)


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
        factories.MonetaryUnitFactory.create(code="GBP")

        # Setup measures
        factories.MeasureTypeFactory.create(sid=695)
        factories.MeasureConditionCodeFactory.create(code="B")
        factories.MeasureActionFactory.create(code="27")
        factories.MeasureActionFactory.create(code="08")

        # Setup regulations
        regulation_group = factories.RegulationGroupFactory.create(
            group_id='ADD',
            description='Additional Duties (AGRI)'
        )
        factories.RegulationFactory(
            regulation_group=regulation_group,
            regulation_id='R0000001'
        )
        factories.RegulationFactory(
            regulation_group=regulation_group,
            regulation_id='R0000002'
        )

        # Setup certificates
        certificate_type = factories.CertificateTypeFactory.create(sid="N")
        factories.CertificateFactory.create(
            sid="990",
            certificate_type=certificate_type
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
            sid=103,
            area_id='US',
            area_code=0
        )
        factories.GeographicalAreaDescriptionFactory.create(
            area=area,
            description='United States of America'
        )

        # Footnotes
        ftn = factories.FootnoteTypeFactory.create(footnote_type_id='FN')
        factories.FootnoteFactory.create(footnote_id='001', footnote_type=ftn)
        factories.FootnoteFactory.create(footnote_id='002', footnote_type=ftn)
        factories.FootnoteFactory.create(footnote_id='003', footnote_type=ftn)
        factories.FootnoteFactory.create(footnote_id='004', footnote_type=ftn)

    @override_settings(DATA_IMPORT_USERNAME='Alice')
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
        - restart of measure (1?) for CC 1100000000 on 01/01/21
            - footnote FN003
            - duty amount 30
        - restart of measure (2?) for CC 1200000000 on 01/01/21
            - footnote FN001, FN002, FN004?
            - duty amount 25
        - new measure (3?) for CC 3900000000 on 01/01/21
            - duty amount 1
        """
        args = [
            fixture_path + 'trade_disputes/new_measures.xlsx',
            fixture_path + 'trade_disputes/existing_measures.xlsx',
        ]
        with output() as xml_output:
            opts = {
                'new_skip_rows': 3,
                'old_skip_rows': 1,
                'measure_sid': 1,
                'measure_condition_sid': 1,
                'transaction_id': 1,
                'output': xml_output.name
            }
            call_command(
                'import_trade_disputes', *args, **opts
            )
            expected_xml_output = fixture_path + 'trade_disputes/expected_output.xml'
            diff = main.diff_files(
                xml_output,
                expected_xml_output,
            )
            assert not diff, f"Unexpected output: {diff}"


class TestImportCountries:

    @override_settings(DATA_IMPORT_USERNAME='Alice')
    def test_update_area_description(self):
        """
        Expected output:
        - description for geographical area with sid 1 changed to Andorra

        """
        factories.UserFactory.create(username='Alice')
        geo_area = factories.GeographicalAreaFactory.create(
            sid=1,
            area_id='AD',
            area_code=0,
        )
        factories.GeographicalAreaDescriptionFactory.create(
            sid=1,
            area=geo_area,
            description='old description',
        )
        args = [
            fixture_path + 'countries/countries-territories-and-regions.xlsx',
            'Sheet1'
        ]
        with output() as xml_output:
            opts = {
                'skip_rows': 1,
                'transaction_id': 1,
                'output': xml_output.name
            }
            call_command(
                'import_countries', *args, **opts
            )
            expected_xml_output = fixture_path + 'countries/expected_output.xml'
            diff = main.diff_files(
                xml_output,
                expected_xml_output,
            )
            assert not diff, f"Unexpected output: {diff}"
            # assert geo_description.description == 'Andorra'
