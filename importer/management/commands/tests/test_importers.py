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
from geo_areas.models import GeographicalArea, GeographicalAreaDescription
from importer.management.commands import import_export_controls_ogd, import_reliefs
from importer.management.commands import import_prohibition_and_restriction
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


class TestQuotaExclusions:
    def setup(self):
        # Add user
        factories.UserFactory.create(username="Alice")

        # Setup measures
        factories.MeasureTypeFactory.create(
            sid='112',
        )
        factories.MeasureTypeFactory.create(
            sid='115',
        )
        factories.MeasureConditionCodeFactory.create(code="B")
        factories.MeasureActionFactory.create(code="27")
        factories.MeasureActionFactory.create(code="08")

        factories.DutyExpressionFactory.create(
            sid=1,
            prefix="",
            duty_amount_applicability_code=ApplicabilityCode.MANDATORY,
            measurement_unit_applicability_code=ApplicabilityCode.PERMITTED,
            monetary_unit_applicability_code=ApplicabilityCode.PERMITTED,
        )

        # Setup good nomenclature
        root_cc = factories.GoodsNomenclatureFactory.create(
            sid="1000",
            item_id="1000000000",
            suffix="80",
            valid_between=DateTimeTZRange(START_TIME, None),
        )

        # Setup geographical area's
        factories.GeographicalAreaFactory.create(
            sid=400, area_id="1011", area_code=1
        )
        # Setup geographical area's
        factories.GeographicalAreaFactory.create(
            sid=400, area_id="1013", area_code=1
        )

    @override_settings(DATA_IMPORT_USERNAME="Alice")
    def test_import_ttr(self):
        """
        Expected output:

        """
        args = [
            fixture_path + "import_ttr/existing_measures.xlsx"
        ]
        with output() as xml_output:
            opts = {
                "transaction_id": 1,
                "measure_sid": 1,
                "envelope_id": 1,
                "output": xml_output.name,
            }
            call_command("import_ttr", *args, **opts)
            expected_xml_output = fixture_path + "import_ttr/expected_output.xml"
            diff = main.diff_files(
                xml_output,
                expected_xml_output,
            )
            assert not diff, f"Unexpected output: {diff}"


class TestImportTTR:
    def setup(self):
        # Add user
        factories.UserFactory.create(username="Alice")

        # Setup measures
        factories.MeasureTypeFactory.create(
            sid='112',
        )
        factories.MeasureTypeFactory.create(
            sid='115',
        )
        factories.MeasureConditionCodeFactory.create(code="B")
        factories.MeasureActionFactory.create(code="27")
        factories.MeasureActionFactory.create(code="08")

        factories.DutyExpressionFactory.create(
            sid=1,
            prefix="",
            duty_amount_applicability_code=ApplicabilityCode.MANDATORY,
            measurement_unit_applicability_code=ApplicabilityCode.PERMITTED,
            monetary_unit_applicability_code=ApplicabilityCode.PERMITTED,
        )

        # Setup certificates
        certificate_type_N = factories.CertificateTypeFactory.create(sid="N")
        factories.CertificateFactory.create(
            sid="990", certificate_type=certificate_type_N
        )

        # Setup regulations
        regulation_group = factories.RegulationGroupFactory.create(
            group_id="SUS",
            description="Erga Omnes Suspensions",
            valid_between=DateTimeTZRange(START_TIME, None),
        )
        factories.RegulationFactory.create(
            regulation_group=regulation_group,
            regulation_id="C2100003",
            role_type=1,
            valid_between=DateTimeTZRange(START_TIME, None),
        )

        # Setup good nomenclature
        root_cc = factories.GoodsNomenclatureFactory.create(
            sid="1000",
            item_id="1000000000",
            suffix="80",
            valid_between=DateTimeTZRange(START_TIME, None),
        )
        make_child(
            root_cc,
            sid="1100",
            item_id="1100000000",
            suffix="80",
            valid_between=DateTimeTZRange(START_TIME, None)
        )
        make_child(
            root_cc,
            sid="1200",
            item_id="1200000000",
            suffix="80",
            valid_between=DateTimeTZRange(START_TIME, None)
        )

        # Setup geographical area's
        factories.GeographicalAreaFactory.create(
            sid=400, area_id="1011", area_code=1
        )

    @override_settings(DATA_IMPORT_USERNAME="Alice")
    def test_import_ttr(self):
        """
        Expected output:

        """
        args = [
            fixture_path + "import_ttr/existing_measures.xlsx"
        ]
        with output() as xml_output:
            opts = {
                "transaction_id": 1,
                "measure_sid": 1,
                "envelope_id": 1,
                "output": xml_output.name,
            }
            call_command("import_ttr", *args, **opts)
            expected_xml_output = fixture_path + "import_ttr/expected_output.xml"
            diff = main.diff_files(
                xml_output,
                expected_xml_output,
            )
            assert not diff, f"Unexpected output: {diff}"


class TestUpdateSuspensions:
    def setup(self):
        # Add user
        factories.UserFactory.create(username="Alice")

        # Setup measures
        factories.MeasureTypeFactory.create(
            sid='112',
        )
        factories.MeasureTypeFactory.create(
            sid='115',
        )
        factories.MeasureConditionCodeFactory.create(code="B")
        factories.MeasureActionFactory.create(code="27")
        factories.MeasureActionFactory.create(code="08")

        factories.DutyExpressionFactory.create(
            sid=1,
            prefix="",
            duty_amount_applicability_code=ApplicabilityCode.MANDATORY,
            measurement_unit_applicability_code=ApplicabilityCode.PERMITTED,
            monetary_unit_applicability_code=ApplicabilityCode.PERMITTED,
        )

        # Setup certificates
        certificate_type_N = factories.CertificateTypeFactory.create(sid="N")
        factories.CertificateFactory.create(
            sid="990", certificate_type=certificate_type_N
        )

        # Setup regulations
        regulation_group = factories.RegulationGroupFactory.create(
            group_id="SUS",
            description="Erga Omnes Suspensions",
            valid_between=DateTimeTZRange(START_TIME, None),
        )
        factories.RegulationFactory.create(
            regulation_group=regulation_group,
            regulation_id="C2100003",
            role_type=1,
            valid_between=DateTimeTZRange(START_TIME, None),
        )
        factories.RegulationFactory.create(
            regulation_group=regulation_group,
            regulation_id="R1921971",
            role_type=4,
            valid_between=DateTimeTZRange(START_TIME, None),
        )

        # Setup good nomenclature
        factories.GoodsNomenclatureFactory.create(
            sid="99673",
            item_id="0709591010",
            suffix="80",
            valid_between=DateTimeTZRange(START_TIME, None),
        )
        factories.GoodsNomenclatureFactory.create(
            sid="99674",
            item_id="0302511020",
            suffix="80",
            valid_between=DateTimeTZRange(START_TIME, None),
        )

        # Setup geographical area's
        factories.GeographicalAreaFactory.create(
            sid=400, area_id="1011", area_code=1
        )

        # Footnotes
        factories.FootnoteFactory.create(
            footnote_id="001",
            footnote_type=factories.FootnoteTypeFactory.create(
                footnote_type_id="EU"
            )
        )
        footnote_type_tm = factories.FootnoteTypeFactory.create(
            footnote_type_id="TM"
        )
        factories.FootnoteFactory.create(
            footnote_id="851",
            footnote_type=footnote_type_tm
        )
        factories.FootnoteFactory.create(
            footnote_id="861",
            footnote_type=footnote_type_tm
        )
        factories.FootnoteFactory.create(
            footnote_id="062",
            footnote_type=footnote_type_tm
        )
        factories.FootnoteFactory.create(
            footnote_id="026",
            footnote_type=footnote_type_tm
        )

    @override_settings(DATA_IMPORT_USERNAME="Alice")
    def test_update_suspensions(self):
        """
        Expected output:

        """
        args = [
            fixture_path + "update_suspensions/existing_measures.xlsx"
        ]
        with output() as xml_output:
            opts = {
                "transaction_id": 1,
                "measure_sid": 1,
                "measure_condition_sid": 1,
                "footnote_description_sid": 1,
                "envelope_id": 1,
                "output": xml_output.name,
            }
            call_command("update_suspensions", *args, **opts)
            expected_xml_output = fixture_path + "update_suspensions/expected_output.xml"
            diff = main.diff_files(
                xml_output,
                expected_xml_output,
            )
            assert not diff, f"Unexpected output: {diff}"


class TestTerminateEUMeasures:
    def setup(self):
        # Add user
        factories.UserFactory.create(username="Alice")

        # Setup regulations
        factories.RegulationFactory.create(
            regulation_id="A8500010",
            role_type=1,
            valid_between=DateTimeTZRange(START_TIME, None),
        )

        # Setup good nomenclature
        factories.GoodsNomenclatureFactory.create(
            sid="1000",
            item_id="1000000000",
            suffix="80",
            valid_between=DateTimeTZRange(START_TIME, None),
        )

        # Setup geographical area's
        factories.GeographicalAreaFactory.create(
            sid=400, area_id="1011", area_code=1
        )

        # Setup measures
        factories.MeasureTypeFactory.create(
            sid='142',
        )

    @override_settings(DATA_IMPORT_USERNAME="Alice")
    def test_terminate_eu_measures(self):
        """
        Expected output:

        """
        args = [
            fixture_path + "terminate_eu_measures/existing_measures.xlsx",
        ]
        with output() as xml_output:
            opts = {
                "transaction_id": 1,
                "envelope_id": 1,
                "output": xml_output.name,
                "old_skip_rows": 1,
            }
            call_command("terminate_eu_measures", *args, **opts)
            expected_xml_output = fixture_path + "terminate_eu_measures/expected_output.xml"
            diff = main.diff_files(
                xml_output,
                expected_xml_output,
            )
            assert not diff, f"Unexpected output: {diff}"


class TestAdjustGeoAreas:
    def add_members(self, group_area, members):
        for sid, area_id in members:
            try:
                member_area = GeographicalArea.objects.get(sid=sid)
            except GeographicalArea.DoesNotExist:
                member_area = factories.GeographicalAreaFactory.create(
                    sid=sid, area_id=area_id, area_code=0,
                    valid_between=DateTimeTZRange(START_TIME, None),
                )
            factories.GeographicalMembershipFactory.create(
                geo_group=group_area,
                member=member_area,
                valid_between=DateTimeTZRange(START_TIME, None),
            )

    def setup(self):
        # Add user
        factories.UserFactory.create(username="Alice")

        # Geo Areas
        # EU
        self.add_members(
            group_area=factories.GeographicalAreaFactory.create(
                sid=349, area_id="1013", area_code=1,
                valid_between=DateTimeTZRange(START_TIME, None),
            ),
            members=[
                (36, 'PL'),
                (47, 'DK'),
                (90, 'AT'),
                (91, 'SE'),
                (92, 'SI'),
                (104, 'CZ'),
                (106, 'DE'),
                (117, 'LT'),
                (118, 'LU'),
                (122, 'GR'),
                (148, 'EE'),
                (153, 'HU'),
                (169, 'EU'),
                (195, 'NL'),
                (236, 'BE'),
                (256, 'SK'),
                (264, 'ES'),
                (265, 'FI'),
                (266, 'FR'),
                (270, 'IT'),
                (317, 'BG'),
                (340, 'LV'),
                (390, 'CY'),
                (395, 'HR'),
                (397, 'IE'),
                (403, 'MT'),
                (428, 'PT'),
                (430, 'RO'),
            ]
        )
        # ERGA OMNES
        self.add_members(
            group_area=factories.GeographicalAreaFactory.create(
                sid=400, area_id="1011", area_code=1,
                valid_between=DateTimeTZRange(START_TIME, None),      
            ),
            members=[
                (-1010161124, 'ZU'),
                (-1010161121, 'ZN'),
                (-1010161118, 'ZH'),
                (-1010161115, 'ZE'),
                (-1010161112, 'ZG'),
                (-1010161109, 'ZF'),
                (-1010161104, 'ZD'),
                (-1010161099, 'ZB'),
                (31, 'GS'),
                (32, 'NF'),
                (33, 'CK'),
                (34, 'NU'),
                (35, 'NR'),
                (36, 'PL'),
                (37, 'AR'),
                (38, 'RW'),
                (39, 'SA'),
                (40, 'SH'),
                (41, 'SL'),
                (42, 'BS'),
                (44, 'SV'),
                (45, 'UZ'),
                (46, 'VE'),
                (47, 'DK'),
                (48, 'YE'),
                (49, 'GL'),
                (50, 'GM'),
                (53, 'IS'),
                (54, 'JM'),
                (57, 'LY'),
                (58, 'MH'),
                (59, 'MX'),
                (67, 'TL'),
                (76, 'SZ'),
                (85, 'HM'),
                (86, 'PS'),
                (88, 'XK'),
                (89, 'PK'),
                (90, 'AT'),
                (91, 'SE'),
                (92, 'SI'),
                (93, 'BN'),
                (94, 'BR'),
                (95, 'SR'),
                (96, 'BW'),
                (97, 'BY'),
                (98, 'TH'),
                (99, 'TO'),
                (100, 'TR'),
                (101, 'CR'),
                (102, 'TW'),
                (103, 'US'),
                (104, 'CZ'),
                (105, 'VA'),
                (106, 'DE'),
                (107, 'VU'),
                (108, 'DZ'),
                (109, 'EG'),
                (111, 'GE'),
                (112, 'GN'),
                (113, 'GY'),
                (115, 'KP'),
                (116, 'LA'),
                (117, 'LT'),
                (118, 'LU'),
                (119, 'NE'),
                (120, 'GD'),
                (121, 'ER'),
                (122, 'GR'),
                (138, 'AQ'),
                (140, 'AD'),
                (141, 'PE'),
                (142, 'AM'),
                (143, 'PN'),
                (144, 'BB'),
                (145, 'SY'),
                (146, 'CA'),
                (148, 'EE'),
                (149, 'ET'),
                (150, 'FK'),
                (151, 'ZM'),
                (152, 'GT'),
                (153, 'HU'),
                (154, 'IN'),
                (155, 'IO'),
                (156, 'JP'),
                (157, 'KE'),
                (159, 'MA'),
                (160, 'ML'),
                (161, 'MN'),
                (162, 'NG'),
                (169, 'EU'),
                (180, 'MK'),
                (191, 'CC'),
                (192, 'CX'),
                (195, 'NL'),
                (196, 'AF'),
                (197, 'PF'),
                (199, 'RU'),
                (200, 'SC'),
                (201, 'SD'),
                (202, 'BJ'),
                (203, 'TD'),
                (204, 'TG'),
                (205, 'CL'),
                (206, 'CU'),
                (207, 'DJ'),
                (208, 'VI'),
                (209, 'DM'),
                (210, 'FJ'),
                (211, 'GH'),
                (213, 'HK'),
                (214, 'ID'),
                (219, 'KY'),
                (221, 'MO'),
                (222, 'MU'),
                (223, 'MV'),
                (236, 'BE'),
                (239, 'MM'),
                (244, 'QS'),
                (247, 'BV'),
                (249, 'QU'),
                (251, 'QW'),
                (252, 'NO'),
                (253, 'AG'),
                (254, 'PG'),
                (255, 'AZ'),
                (256, 'SK'),
                (257, 'SN'),
                (258, 'BM'),
                (259, 'TN'),
                (260, 'CM'),
                (261, 'TT'),
                (262, 'UG'),
                (263, 'DO'),
                (264, 'ES'),
                (265, 'FI'),
                (266, 'FR'),
                (267, 'GI'),
                (268, 'HN'),
                (269, 'IQ'),
                (270, 'IT'),
                (272, 'KG'),
                (273, 'KR'),
                (274, 'KW'),
                (275, 'KZ'),
                (276, 'LB'),
                (277, 'LC'),
                (278, 'LR'),
                (279, 'MD'),
                (280, 'MR'),
                (281, 'MW'),
                (282, 'MY'),
                (283, 'MZ'),
                (284, 'NA'),
                (286, 'LI'),
                (295, 'CD'),
                (296, 'XL'),
                (306, 'GU'),
                (307, 'TK'),
                (311, 'NP'),
                (312, 'AE'),
                (313, 'PA'),
                (314, 'AI'),
                (315, 'QA'),
                (316, 'SG'),
                (317, 'BG'),
                (318, 'BH'),
                (319, 'BO'),
                (320, 'BZ'),
                (321, 'TM'),
                (322, 'CO'),
                (324, 'UY'),
                (325, 'VC'),
                (326, 'EC'),
                (327, 'WS'),
                (328, 'XC'),
                (330, 'FO'),
                (333, 'ZW'),
                (334, 'IL'),
                (335, 'IR'),
                (336, 'KH'),
                (337, 'KI'),
                (338, 'KM'),
                (339, 'LK'),
                (340, 'LV'),
                (341, 'MG'),
                (342, 'NC'),
                (343, 'MP'),
                (346, 'XS'),
                (348, 'ME'),
                (369, 'AS'),
                (370, 'TF'),
                (374, 'NI'),
                (375, 'OM'),
                (376, 'AL'),
                (377, 'AU'),
                (378, 'AW'),
                (379, 'SB'),
                (380, 'BF'),
                (381, 'BI'),
                (382, 'SM'),
                (383, 'SO'),
                (384, 'TC'),
                (385, 'CI'),
                (386, 'TV'),
                (387, 'TZ'),
                (388, 'UA'),
                (389, 'CV'),
                (390, 'CY'),
                (391, 'VG'),
                (392, 'VN'),
                (393, 'WF'),
                (394, 'GW'),
                (395, 'HR'),
                (396, 'HT'),
                (397, 'IE'),
                (402, 'LS'),
                (403, 'MT'),
                (405, 'PW'),
                (406, 'MS'),
                (422, 'QQ'),
                (424, 'UM'),
                (425, 'NZ'),
                (426, 'PH'),
                (427, 'PM'),
                (428, 'PT'),
                (429, 'PY'),
                (430, 'RO'),
                (431, 'BA'),
                (432, 'BD'),
                (433, 'ST'),
                (434, 'BT'),
                (435, 'CF'),
                (436, 'CG'),
                (437, 'CH'),
                (438, 'TJ'),
                (439, 'CN'),
                (440, 'FM'),
                (441, 'GA'),
                (442, 'ZA'),
                (443, 'GQ'),
                (444, 'JO'),
                (446, 'KN'),
                (448, 'AO'),
                (456, 'BL'),
                (457, 'SS'),
                (458, 'BQ'),
                (459, 'CW'),
                (460, 'SX'),
                (461, 'EH'),
                (462, 'QP'),
            ]

        )

        # GSP
        self.add_members(
            group_area=factories.GeographicalAreaFactory.create(
                sid=217, area_id="2020", area_code=1,
                valid_between=DateTimeTZRange(START_TIME, None),
            ),
            members=[
                (33, 'CK'),
                (34, 'NU'),
                (45, 'UZ'),
                (108, 'DZ'),
                (145, 'SY'),
                (154, 'IN'),
                (157, 'KE'),
                (162, 'NG'),
                (214, 'ID'),
                (392, 'VN'),
                (436, 'CG'),
                (438, 'TJ'),
                (440, 'FM'),
            ]
        )
        # factories.GeographicalAreaFactory.create(
        #     sid=260, area_id="CM", area_code=0,
        #     valid_between=DateTimeTZRange(START_TIME, None),
        # )   # Cameroon
        # factories.GeographicalAreaFactory.create(
        #     sid=211, area_id="GH", area_code=0,
        #     valid_between=DateTimeTZRange(START_TIME, None),
        # )   # Ghana
        # factories.GeographicalAreaFactory.create(
        #     sid=279, area_id="MD", area_code=0,
        #     valid_between=DateTimeTZRange(START_TIME, None),
        # )   # Moldova

        # All Third Countries
        self.add_members(
            group_area=factories.GeographicalAreaFactory.create(
                sid=68, area_id="1008", area_code=1,
                valid_between=DateTimeTZRange(START_TIME, None),
            ),
            members=[
                (31, 'GS'),
                (32, 'NF'),
                (33, 'CK'),
                (34, 'NU'),
                (35, 'NR'),
                (37, 'AR'),
                (38, 'RW'),
                (39, 'SA'),
                (40, 'SH'),
                (41, 'SL'),
                (42, 'BS'),
                (44, 'SV'),
                (45, 'UZ'),
                (46, 'VE'),
                (48, 'YE'),
                (49, 'GL'),
                (50, 'GM'),
                (53, 'IS'),
                (54, 'JM'),
                (57, 'LY'),
                (58, 'MH'),
                (59, 'MX'),
                (67, 'TL'),
                (76, 'SZ'),
                (85, 'HM'),
                (86, 'PS'),
                (88, 'XK'),
                (89, 'PK'),
                (93, 'BN'),
                (94, 'BR'),
                (95, 'SR'),
                (96, 'BW'),
                (97, 'BY'),
                (98, 'TH'),
                (99, 'TO'),
                (100, 'TR'),
                (101, 'CR'),
                (102, 'TW'),
                (103, 'US'),
                (105, 'VA'),
                (107, 'VU'),
                (108, 'DZ'),
                (109, 'EG'),
                (111, 'GE'),
                (112, 'GN'),
                (113, 'GY'),
                (115, 'KP'),
                (116, 'LA'),
                (119, 'NE'),
                (120, 'GD'),
                (121, 'ER'),
                (138, 'AQ'),
                (140, 'AD'),
                (141, 'PE'),
                (142, 'AM'),
                (143, 'PN'),
                (144, 'BB'),
                (145, 'SY'),
                (146, 'CA'),
                (149, 'ET'),
                (150, 'FK'),
                (151, 'ZM'),
                (152, 'GT'),
                (154, 'IN'),
                (155, 'IO'),
                (156, 'JP'),
                (157, 'KE'),
                (159, 'MA'),
                (160, 'ML'),
                (161, 'MN'),
                (162, 'NG'),
                (180, 'MK'),
                (191, 'CC'),
                (192, 'CX'),
                (196, 'AF'),
                (197, 'PF'),
                (199, 'RU'),
                (200, 'SC'),
                (201, 'SD'),
                (202, 'BJ'),
                (203, 'TD'),
                (204, 'TG'),
                (205, 'CL'),
                (206, 'CU'),
                (207, 'DJ'),
                (208, 'VI'),
                (209, 'DM'),
                (210, 'FJ'),
                (211, 'GH'),
                (213, 'HK'),
                (214, 'ID'),
                (219, 'KY'),
                (221, 'MO'),
                (222, 'MU'),
                (223, 'MV'),
                (239, 'MM'),
                (244, 'QS'),
                (247, 'BV'),
                (249, 'QU'),
                (251, 'QW'),
                (252, 'NO'),
                (253, 'AG'),
                (254, 'PG'),
                (255, 'AZ'),
                (257, 'SN'),
                (258, 'BM'),
                (259, 'TN'),
                (260, 'CM'),
                (261, 'TT'),
                (262, 'UG'),
                (263, 'DO'),
                (267, 'GI'),
                (268, 'HN'),
                (269, 'IQ'),
                (272, 'KG'),
                (273, 'KR'),
                (274, 'KW'),
                (275, 'KZ'),
                (276, 'LB'),
                (277, 'LC'),
                (278, 'LR'),
                (279, 'MD'),
                (280, 'MR'),
                (281, 'MW'),
                (282, 'MY'),
                (283, 'MZ'),
                (284, 'NA'),
                (286, 'LI'),
                (295, 'CD'),
                (296, 'XL'),
                (306, 'GU'),
                (307, 'TK'),
                (311, 'NP'),
                (312, 'AE'),
                (313, 'PA'),
                (314, 'AI'),
                (315, 'QA'),
                (316, 'SG'),
                (318, 'BH'),
                (319, 'BO'),
                (320, 'BZ'),
                (321, 'TM'),
                (322, 'CO'),
                (324, 'UY'),
                (325, 'VC'),
                (326, 'EC'),
                (327, 'WS'),
                (328, 'XC'),
                (330, 'FO'),
                (333, 'ZW'),
                (334, 'IL'),
                (335, 'IR'),
                (336, 'KH'),
                (337, 'KI'),
                (338, 'KM'),
                (339, 'LK'),
                (341, 'MG'),
                (342, 'NC'),
                (343, 'MP'),
                (346, 'XS'),
                (348, 'ME'),
                (369, 'AS'),
                (370, 'TF'),
                (374, 'NI'),
                (375, 'OM'),
                (376, 'AL'),
                (377, 'AU'),
                (378, 'AW'),
                (379, 'SB'),
                (380, 'BF'),
                (381, 'BI'),
                (382, 'SM'),
                (383, 'SO'),
                (384, 'TC'),
                (385, 'CI'),
                (386, 'TV'),
                (387, 'TZ'),
                (388, 'UA'),
                (389, 'CV'),
                (391, 'VG'),
                (392, 'VN'),
                (393, 'WF'),
                (394, 'GW'),
                (396, 'HT'),
                (402, 'LS'),
                (405, 'PW'),
                (406, 'MS'),
                (422, 'QQ'),
                (424, 'UM'),
                (425, 'NZ'),
                (426, 'PH'),
                (427, 'PM'),
                (429, 'PY'),
                (431, 'BA'),
                (432, 'BD'),
                (433, 'ST'),
                (434, 'BT'),
                (435, 'CF'),
                (436, 'CG'),
                (437, 'CH'),
                (438, 'TJ'),
                (439, 'CN'),
                (440, 'FM'),
                (441, 'GA'),
                (442, 'ZA'),
                (443, 'GQ'),
                (444, 'JO'),
                (446, 'KN'),
                (448, 'AO'),
                (456, 'BL'),
                (457, 'SS'),
                (458, 'BQ'),
                (459, 'CW'),
                (460, 'SX'),
                (461, 'EH'),
                (462, 'QP'),
            ]
        )

        # Members countries of WTO
        self.add_members(
            group_area=factories.GeographicalAreaFactory.create(
                sid=215, area_id="2500", area_code=1,
                valid_between=DateTimeTZRange(START_TIME, None),
            ),
            members=[
                (36, 'PL'),
                (37, 'AR'),
                (38, 'RW'),
                (39, 'SA'),
                (41, 'SL'),
                (44, 'SV'),
                (46, 'VE'),
                (47, 'DK'),
                (48, 'YE'),
                (50, 'GM'),
                (53, 'IS'),
                (54, 'JM'),
                (59, 'MX'),
                (76, 'SZ'),
                (89, 'PK'),
                (90, 'AT'),
                (91, 'SE'),
                (92, 'SI'),
                (93, 'BN'),
                (94, 'BR'),
                (95, 'SR'),
                (96, 'BW'),
                (98, 'TH'),
                (99, 'TO'),
                (100, 'TR'),
                (101, 'CR'),
                (102, 'TW'),
                (103, 'US'),
                (104, 'CZ'),
                (106, 'DE'),
                (107, 'VU'),
                (109, 'EG'),
                (111, 'GE'),
                (112, 'GN'),
                (113, 'GY'),
                (116, 'LA'),
                (117, 'LT'),
                (118, 'LU'),
                (119, 'NE'),
                (120, 'GD'),
                (122, 'GR'),
                (141, 'PE'),
                (142, 'AM'),
                (144, 'BB'),
                (146, 'CA'),
                (148, 'EE'),
                (151, 'ZM'),
                (152, 'GT'),
                (153, 'HU'),
                (154, 'IN'),
                (156, 'JP'),
                (157, 'KE'),
                (159, 'MA'),
                (160, 'ML'),
                (161, 'MN'),
                (162, 'NG'),
                (169, 'EU'),
                (180, 'MK'),
                (195, 'NL'),
                (196, 'AF'),
                (199, 'RU'),
                (200, 'SC'),
                (202, 'BJ'),
                (203, 'TD'),
                (204, 'TG'),
                (205, 'CL'),
                (206, 'CU'),
                (207, 'DJ'),
                (209, 'DM'),
                (210, 'FJ'),
                (211, 'GH'),
                (213, 'HK'),
                (214, 'ID'),
                (221, 'MO'),
                (222, 'MU'),
                (223, 'MV'),
                (236, 'BE'),
                (239, 'MM'),
                (252, 'NO'),
                (253, 'AG'),
                (254, 'PG'),
                (256, 'SK'),
                (257, 'SN'),
                (259, 'TN'),
                (260, 'CM'),
                (261, 'TT'),
                (262, 'UG'),
                (263, 'DO'),
                (264, 'ES'),
                (265, 'FI'),
                (266, 'FR'),
                (268, 'HN'),
                (270, 'IT'),
                (272, 'KG'),
                (273, 'KR'),
                (274, 'KW'),
                (275, 'KZ'),
                (277, 'LC'),
                (278, 'LR'),
                (279, 'MD'),
                (280, 'MR'),
                (281, 'MW'),
                (282, 'MY'),
                (283, 'MZ'),
                (284, 'NA'),
                (286, 'LI'),
                (295, 'CD'),
                (311, 'NP'),
                (312, 'AE'),
                (313, 'PA'),
                (315, 'QA'),
                (316, 'SG'),
                (317, 'BG'),
                (318, 'BH'),
                (319, 'BO'),
                (320, 'BZ'),
                (322, 'CO'),
                (324, 'UY'),
                (325, 'VC'),
                (326, 'EC'),
                (327, 'WS'),
                (333, 'ZW'),
                (334, 'IL'),
                (336, 'KH'),
                (339, 'LK'),
                (340, 'LV'),
                (341, 'MG'),
                (348, 'ME'),
                (374, 'NI'),
                (375, 'OM'),
                (376, 'AL'),
                (377, 'AU'),
                (379, 'SB'),
                (380, 'BF'),
                (381, 'BI'),
                (385, 'CI'),
                (387, 'TZ'),
                (388, 'UA'),
                (389, 'CV'),
                (390, 'CY'),
                (392, 'VN'),
                (394, 'GW'),
                (395, 'HR'),
                (396, 'HT'),
                (397, 'IE'),
                (402, 'LS'),
                (403, 'MT'),
                (425, 'NZ'),
                (426, 'PH'),
                (428, 'PT'),
                (429, 'PY'),
                (430, 'RO'),
                (432, 'BD'),
                (435, 'CF'),
                (436, 'CG'),
                (437, 'CH'),
                (438, 'TJ'),
                (439, 'CN'),
                (441, 'GA'),
                (442, 'ZA'),
                (444, 'JO'),
                (446, 'KN'),
                (448, 'AO'),
            ]
        )

        # OCTs(Overseas Countries and Territories)
        self.add_members(
            group_area=factories.GeographicalAreaFactory.create(
                sid=445, area_id="2080", area_code=1,
                valid_between=DateTimeTZRange(START_TIME, None),
            ),
            members=[
                (31, 'GS'),
                (40, 'SH'),
                (49, 'GL'),
                (138, 'AQ'),
                (143, 'PN'),
                (150, 'FK'),
                (155, 'IO'),
                (197, 'PF'),
                (219, 'KY'),
                (258, 'BM'),
                (314, 'AI'),
                (342, 'NC'),
                (370, 'TF'),
                (378, 'AW'),
                (384, 'TC'),
                (391, 'VG'),
                (393, 'WF'),
                (406, 'MS'),
                (427, 'PM'),
                (456, 'BL'),
                (458, 'BQ'),
                (459, 'CW'),
                (460, 'SX'),
            ]
        )

        # Western balkans
        group_area = factories.GeographicalAreaFactory.create(
            sid=484, area_id="1098", area_code=1,
            valid_between=DateTimeTZRange(START_TIME, None),
        )
        self.add_members(
            group_area=group_area,
            members=[
                (88, 'XK'),
                (180, 'MK'),
                (346, 'XS'),
                (348, 'ME'),
                (376, 'AL'),
                (431, 'BA'),
            ]
        )
        factories.GeographicalAreaDescriptionFactory.create(
            sid=1356,
            area=group_area,
            description="West Balkan Countries (AL, BA, ME, MK, XK, XS)",
            valid_between=DateTimeTZRange(START_TIME, None),
        )

        # EU - Canada agreement: re - imported goods
        factories.GeographicalAreaFactory.create(
            sid=331, area_id="GB", area_code=0,
            valid_between=DateTimeTZRange(START_TIME, None),
        )   # GB
        group_area = factories.GeographicalAreaFactory.create(
            sid=485, area_id="1006", area_code=1,
            valid_between=DateTimeTZRange(START_TIME, None),
        )
        self.add_members(
            group_area=group_area,
            members=[
                (169, 'EU'),
            ]
        )
        factories.GeographicalAreaDescriptionFactory.create(
            sid=1359,
            area=group_area,
            description="EU - Canada agreement: re - imported goods",
            valid_between=DateTimeTZRange(START_TIME, None),
        )
        # EU-Switzerland agreement: re-imported goods
        group_area = factories.GeographicalAreaFactory.create(
            sid=232, area_id="1007", area_code=1,
            valid_between=DateTimeTZRange(START_TIME, None),
        )
        self.add_members(
            group_area=group_area,
            members=[
                (169, 'EU'),
            ]
        )
        factories.GeographicalAreaDescriptionFactory.create(
            sid=1099,
            area=group_area,
            description="EU-Switzerland agreement: re-imported goods",
            valid_between=DateTimeTZRange(START_TIME, None),
        )

        # Steel safeguards
        self.add_members(
            group_area=factories.GeographicalAreaFactory.create(
                sid=496, area_id="5050", area_code=1,
                valid_between=DateTimeTZRange(START_TIME, None),
            ),
            members=[
                (31, 'GS'),
                (32, 'NF'),
                (33, 'CK'),
                (34, 'NU'),
                (35, 'NR'),
                (39, 'SA'),
                (40, 'SH'),
                (45, 'UZ'),
                (49, 'GL'),
                (53, 'IS'),
                (57, 'LY'),
                (58, 'MH'),
                (67, 'TL'),
                (85, 'HM'),
                (86, 'PS'),
                (88, 'XK'),
                (94, 'BR'),
                (97, 'BY'),
                (98, 'TH'),
                (100, 'TR'),
                (102, 'TW'),
                (103, 'US'),
                (105, 'VA'),
                (108, 'DZ'),
                (115, 'KP'),
                (121, 'ER'),
                (138, 'AQ'),
                (140, 'AD'),
                (143, 'PN'),
                (145, 'SY'),
                (146, 'CA'),
                (149, 'ET'),
                (150, 'FK'),
                (154, 'IN'),
                (155, 'IO'),
                (156, 'JP'),
                (169, 'EU'),
                (180, 'MK'),
                (191, 'CC'),
                (192, 'CX'),
                (197, 'PF'),
                (199, 'RU'),
                (201, 'SD'),
                (208, 'VI'),
                (219, 'KY'),
                (244, 'QS'),
                (247, 'BV'),
                (249, 'QU'),
                (251, 'QW'),
                (252, 'NO'),
                (255, 'AZ'),
                (258, 'BM'),
                (267, 'GI'),
                (269, 'IQ'),
                (273, 'KR'),
                (276, 'LB'),
                (286, 'LI'),
                (296, 'XL'),
                (306, 'GU'),
                (307, 'TK'),
                (312, 'AE'),
                (314, 'AI'),
                (316, 'SG'),
                (321, 'TM'),
                (328, 'XC'),
                (330, 'FO'),
                (334, 'IL'),
                (335, 'IR'),
                (337, 'KI'),
                (338, 'KM'),
                (342, 'NC'),
                (343, 'MP'),
                (346, 'XS'),
                (369, 'AS'),
                (370, 'TF'),
                (377, 'AU'),
                (378, 'AW'),
                (382, 'SM'),
                (383, 'SO'),
                (384, 'TC'),
                (386, 'TV'),
                (388, 'UA'),
                (391, 'VG'),
                (392, 'VN'),
                (393, 'WF'),
                (405, 'PW'),
                (406, 'MS'),
                (422, 'QQ'),
                (424, 'UM'),
                (425, 'NZ'),
                (427, 'PM'),
                (431, 'BA'),
                (433, 'ST'),
                (434, 'BT'),
                (437, 'CH'),
                (439, 'CN'),
                (440, 'FM'),
                (443, 'GQ'),
                (456, 'BL'),
                (457, 'SS'),
                (458, 'BQ'),
                (459, 'CW'),
                (460, 'SX'),
                (461, 'EH'),
                (462, 'QP'),
            ]
        )

        # Eastern and Southern Africa States
        self.add_members(
            group_area=factories.GeographicalAreaFactory.create(
                sid=455, area_id="1034", area_code=1,
                valid_between=DateTimeTZRange(START_TIME, None),
            ),
            members=[
                (200, 'SC'),
                (222, 'MU'),
                (333, 'ZW'),
                (338, 'KM'),
                (341, 'MG'),
            ]
        )

    @override_settings(DATA_IMPORT_USERNAME="Alice")
    def test_adjust_geo_areas(self):
        """
        Expected output:

        """
        args = []
        with output() as xml_output:
            opts = {
                "transaction_id": 1,
                "envelope_id": 1,
                "group_area_sid": 1,
                "group_area_description_sid": 1,
                "output": xml_output.name,
            }
            call_command("adjust_geo_areas", *args, **opts)
            expected_xml_output = fixture_path + "adjust_geo_areas/expected_output.xml"
            diff = main.diff_files(
                xml_output,
                expected_xml_output,
            )
            assert not diff, f"Unexpected output: {diff}"


class TestApproveDraftRegulations:
    def setup(self):
        # Add user
        factories.UserFactory.create(username="Alice")

        groups = [
            'DNC',
            'SPG',
            'SUS',
            'TXC',
            'DUM',
            'FTA',
            'KON',
            'UKR',
            'MLA',
            'PRF',
            'PRS',
        ]
        for group_id in groups:
            regulation_group = factories.RegulationGroupFactory.create(
                group_id=group_id,
                valid_between=DateTimeTZRange(START_TIME, None),
            )

    @override_settings(DATA_IMPORT_USERNAME="Alice")
    def test_approve_draft_regulations(self):
        """
        Expected output:

        """
        args = [
        ]
        with output() as xml_output:
            opts = {
                "transaction_id": 1,
                "envelope_id": 1,
                "output": xml_output.name,
            }
            call_command("approve_draft_regulations", *args, **opts)
            expected_xml_output = fixture_path + "approve_draft_regulations/expected_output.xml"
            diff = main.diff_files(
                xml_output,
                expected_xml_output,
            )
            assert not diff, f"Unexpected output: {diff}"


class TestImportReliefs:
    def setup(self):
        # Add user
        factories.UserFactory.create(username="Alice")

        # Setup measures
        factories.MeasureTypeFactory.create(
            sid='117',
            description=f'Suspension - goods for certain categories of ships, boats and other vessels and for drilling or production platforms',
        )
        factories.MeasureConditionCodeFactory.create(code="B")
        factories.MeasureActionFactory.create(code="27")
        factories.MeasureActionFactory.create(code="07")

        factories.DutyExpressionFactory.create(
            sid=1,
            prefix="",
            duty_amount_applicability_code=ApplicabilityCode.MANDATORY,
            measurement_unit_applicability_code=ApplicabilityCode.PERMITTED,
            monetary_unit_applicability_code=ApplicabilityCode.PERMITTED,
        )

        # Setup certificates
        certificate_type_C = factories.CertificateTypeFactory.create(sid="C")
        factories.CertificateFactory.create(
            sid="990", certificate_type=certificate_type_C
        )

        # Setup regulations
        regulation_group = factories.RegulationGroupFactory.create(
            group_id="SUS",
            description="Erga Omnes Suspensions",
            valid_between=DateTimeTZRange(START_TIME, None),
        )
        factories.RegulationFactory.create(
            regulation_group=regulation_group,
            regulation_id="R8726583",
            role_type=1,
            valid_between=DateTimeTZRange(START_TIME, None),
        )

        # Setup good nomenclature
        factories.GoodsNomenclatureFactory.create(
            sid="1000",
            item_id="1000000000",
            suffix="80",
            valid_between=DateTimeTZRange(START_TIME, None),
        )

        # Setup geographical area's
        factories.GeographicalAreaFactory.create(
            sid=400, area_id="1011", area_code=1
        )

        # Footnotes
        factories.FootnoteFactory.create(
            footnote_id="003",
            footnote_type=factories.FootnoteTypeFactory.create(
                footnote_type_id="EU"
            )
        )
        factories.FootnoteFactory.create(
            footnote_id="511",
            footnote_type=factories.FootnoteTypeFactory.create(
                footnote_type_id="TM"
            )
        )

    @patch.object(
        import_reliefs,
        'MEASURE_TYPES',
        ['117']
    )
    @patch.object(
        import_reliefs,
        'NEW_REGULATIONS',
        ['S1812490']
    )
    @patch.dict(
        'importer.management.commands.import_reliefs.REGULATION_MAPPING_OLD_NEW',
        {
            'R872658': 'S1812490',
        },
        clear=True
    )
    @override_settings(DATA_IMPORT_USERNAME="Alice")
    def test_import_reliefs(self):
        """
        Expected output:

        """
        args = [
            fixture_path + "import_reliefs/existing_measures.xlsx",
        ]
        with output() as xml_output:
            opts = {
                "measure_sid": 1,
                "measure_condition_sid": 1,
                "transaction_id": 1,
                "envelope_id": 1,
                "output": xml_output.name,
                "old_skip_rows": 1,
            }
            call_command("import_reliefs", *args, **opts)
            expected_xml_output = fixture_path + "import_reliefs/expected_output.xml"
            diff = main.diff_files(
                xml_output,
                expected_xml_output,
            )
            assert not diff, f"Unexpected output: {diff}"


class TestIECOGD:
    def setup(self):
        # Add user
        factories.UserFactory.create(username="Alice")

        # Setup measures
        factories.MeasureTypeFactory.create(
            sid='482',
            description=f'Declaration of subheading submitted to restrictions (net weight/supplementary unit)',
        )
        factories.MeasureConditionCodeFactory.create(code="R")
        factories.MeasureActionFactory.create(code="10")
        factories.MeasureActionFactory.create(code="28")
        factories.MeasurementFactory(
            measurement_unit=factories.MeasurementUnitFactory.create(
                code="KGM"
            ),
            measurement_unit_qualifier=None
        )

        # Setup regulations
        regulation_group = factories.RegulationGroupFactory.create(
            group_id="MLA",
            description="Entry into free circulation, Export authorization",
            valid_between=DateTimeTZRange(START_TIME, None),
        )
        factories.RegulationFactory.create(
            regulation_group=regulation_group,
            regulation_id="R1206720",
            role_type=1,
            valid_between=DateTimeTZRange(START_TIME, None),
        )

        # Setup good nomenclature
        factories.GoodsNomenclatureFactory.create(
            sid="1000",
            item_id="1000000000",
            suffix="80",
            valid_between=DateTimeTZRange(START_TIME, None),
        )

        # Setup geographical area's
        factories.GeographicalAreaFactory.create(
            sid=400, area_id="1011", area_code=1
        )

        # Footnotes
        ftn = factories.FootnoteTypeFactory.create(footnote_type_id="CD")
        factories.FootnoteFactory.create(footnote_id="808", footnote_type=ftn)

    @patch.object(
        import_export_controls_ogd,
        'MEASURE_TYPES',
        ['482']
    )
    @patch.object(
        import_export_controls_ogd,
        'NEW_REGULATIONS',
        ['C2100230']
    )
    @patch.dict(
        'importer.management.commands.import_export_controls_ogd.REGULATION_MAPPING_OLD_NEW',
        {
            'R120672': 'C2100230',
        },
        clear=True
    )
    @patch.dict(
        'importer.management.commands.import_export_controls_ogd.REGULATION_MEASURE_TYPE_TRANSFER',
        {
            ('R120672', '482'): True,
        },
        clear=True
    )
    @override_settings(DATA_IMPORT_USERNAME="Alice")
    def test_import_export_control_ogd(self):
        """
        Expected output:

        """
        args = [
            fixture_path + "import_export_controls_ogd/existing_measures.xlsx",
        ]
        with output() as xml_output:
            opts = {
                "measure_sid": 1,
                "measure_condition_sid": 1,
                "transaction_id": 1,
                "envelope_id": 1,
                "output": xml_output.name,
                "old_skip_rows": 1,
            }
            call_command("import_export_controls_ogd", *args, **opts)
            expected_xml_output = fixture_path + "import_export_controls_ogd/expected_output.xml"
            diff = main.diff_files(
                xml_output,
                expected_xml_output,
            )
            assert not diff, f"Unexpected output: {diff}"


class TestPnR:
    def setup(self):
        # Add user
        factories.UserFactory.create(username="Alice")

        # Setup measures
        series_b = factories.MeasureTypeSeriesFactory.create(
            sid='B'
        )
        factories.MeasureTypeFactory.create(
            sid='AHC',
            description=f'description for AHC',
            trade_movement_code=2,
            priority_code=6,
            measure_component_applicability_code=1,
            origin_destination_code=2,
            order_number_capture_code=2,
            measure_explosion_level=10,
            measure_type_series=series_b,

        )
        factories.MeasureTypeFactory.create(
            sid='PRT',
            description=f'description for PRT',
            trade_movement_code=2,
            priority_code=6,
            measure_component_applicability_code=1,
            origin_destination_code=2,
            order_number_capture_code=2,
            measure_explosion_level=10,
        )

        factories.MeasureConditionCodeFactory.create(code="B")
        factories.MeasureConditionCodeFactory.create(code="Z")
        factories.MeasureActionFactory.create(code="24")
        factories.MeasureActionFactory.create(code="04")

        # Setup certificates
        certificate_type_9 = factories.CertificateTypeFactory.create(sid="9")
        factories.CertificateFactory.create(
            sid="111", certificate_type=certificate_type_9
        )
        factories.CertificateFactory.create(
            sid="112", certificate_type=certificate_type_9
        )
        factories.CertificateFactory.create(
            sid="120", certificate_type=certificate_type_9
        )

        # Setup regulations
        regulation_group = factories.RegulationGroupFactory.create(
            group_id="UKR",
            description="UK dummy regulation group for the UK regulations",
            valid_between=DateTimeTZRange(START_TIME, None),
        )
        factories.RegulationFactory.create(
            regulation_group=regulation_group,
            regulation_id="Z1970AHC",
            role_type=1,
            valid_between=DateTimeTZRange(START_TIME, None),
        )
        factories.RegulationFactory.create(
            regulation_group=regulation_group,
            regulation_id="IYY99990",
            role_type=1,
            valid_between=DateTimeTZRange(START_TIME, None),
        )

        # Setup good nomenclature
        factories.GoodsNomenclatureFactory.create(
            sid="1000",
            item_id="1000000000",
            suffix="80",
            valid_between=DateTimeTZRange(START_TIME, None),
        )

        # Setup geographical area's
        factories.GeographicalAreaFactory.create(
            sid=400, area_id="1011", area_code=1
        )
        factories.GeographicalAreaFactory.create(
            sid=497, area_id="6010", area_code=1
        )
        group_area = factories.GeographicalAreaFactory.create(
            sid='-248', area_id="D010", area_code=1
        )
        member_area = factories.GeographicalAreaFactory.create(
            sid='46', area_id="VE", area_code=0
        )
        factories.GeographicalMembershipFactory.create(
            geo_group=group_area,
            member=member_area,
        )

        # Footnotes
        footnote = factories.FootnoteFactory.create(
            footnote_id="003",
            footnote_type=factories.FootnoteTypeFactory.create(
                footnote_type_id="04",
                description='new PR footnote type',
            ),
        )
        factories.FootnoteDescriptionFactory.create(
            described_footnote=footnote,
            description='new PR footnote',
        ),

    @patch.dict(
        'importer.management.commands.import_prohibition_and_restriction.MEASURE_MAPPING_OLD_NEW',
        {
            'AHC': '350',
            'PRT': '362',
        },
        clear=True
    )
    @patch.dict(
        'importer.management.commands.import_prohibition_and_restriction.REGULATION_MAPPING_OLD_NEW',
        {
            'Z1970AHC': 'C2100009',
            'IYY99990': 'C2100020',
        },
        clear=True
    )
    @patch.dict(
        'importer.management.commands.import_prohibition_and_restriction.GEO_AREA_MAPPING_MEMBERS_GROUP_SID_MEMBER_SID',
        {
            '-248': ['46'],
        },
        clear=True
    )
    @patch.dict(
        'importer.management.commands.import_prohibition_and_restriction.GEO_AREA_GROUP_ID_AND_DESCRIPTIONS',
        {
            '-248': ['6010', 'Home Office'],
        },
        clear=True
    )
    @patch.dict(
        'importer.management.commands.import_prohibition_and_restriction.FOOTNOTE_MAPPING_OLD_NEW',
        {
            '04003': 'PR003',
        },
        clear=True
    )
    @patch.object(
        import_prohibition_and_restriction,
        'NEW_FOOTNOTE_TYPES',
        ['PR003'],
    )
    @override_settings(DATA_IMPORT_USERNAME="Alice")
    def test_PnR(self):
        """
        Expected output:
            - new measure type
                - sid 350
                - series B
                - same description/config as old
                - valid from 01-01-2021
            - new measure type 362
            - define draft base regulation C2100009
                - valid from 01-01-2021
                - group UKR
            - define draft base regulation C2100020
            - define geographical area group
                - sid 497
                - id D011
                - description period sid 497
                - description: 'Home Office'
                - membership: 46 Venezuela
            - end measure for CC 1000000000
                - measure type: AHC
                - generating reg: Z1970AHC
                - justifying reg: C2100009
                - end date: 31/12/2020
            - create new measure for CC 1000000000
                - generating reg: C2100009
                - start date: 01/01/2021
                - inherit footnote 04003
                - inherit measure conditions
                    (1)
                    - condition code B
                    - action code 24
                    - certificate type code 9
                    - cert code 120
                    (2)
                    - condition code B
                    - action code 04
                - delete measure for CC 1000000000
                    - measure type: PRT
                    - ...
                - create measure for CC 1000000000
                    - use new country group (6010) instead of old (-248)

        """
        args = [
            fixture_path + "prohibition_and_restriction/existing_measures.xlsx",
        ]
        with output() as xml_output:
            opts = {
                "measure_sid": 1,
                "measure_condition_sid": 1,
                "group_area_sid": 497,
                "group_area_description_sid": 1416,
                "footnote_description_sid": 1,
                "transaction_id": 1,
                "envelope_id": 1,
                "output": xml_output.name,
                "old_skip_rows": 1,
            }
            call_command("import_prohibition_and_restriction", *args, **opts)
            expected_xml_output = fixture_path + "prohibition_and_restriction/expected_output.xml"
            diff = main.diff_files(
                xml_output,
                expected_xml_output,
            )
            assert not diff, f"Unexpected output: {diff}"


class TestImportControls:
    def setup(self):
        # Add user
        factories.UserFactory.create(username="Alice")

        # Setup measures
        for meanure_type_sid in ['728', '277', '475', '711', '465', '707', '760', '714']:
            factories.MeasureTypeFactory.create(sid=meanure_type_sid)
        factories.MeasureConditionCodeFactory.create(code="Y")
        factories.MeasureActionFactory.create(code="29")
        factories.MeasureActionFactory.create(code="09")

        # Setup regulations
        regulation_group = factories.RegulationGroupFactory.create(
            group_id="MLA",
            description="Entry into free circulation, Export authorization",
            valid_between=DateTimeTZRange(START_TIME, None),
        )
        factories.RegulationFactory.create(
            regulation_group=regulation_group,
            regulation_id="R1202670",
            role_type=4,
            valid_between=DateTimeTZRange(START_TIME, None),
        )

        # Setup certificates
        certificate_type_y = factories.CertificateTypeFactory.create(sid="Y")
        certificate_type_c = factories.CertificateTypeFactory.create(sid="C")
        factories.CertificateFactory.create(
            sid="949", certificate_type=certificate_type_y
        )
        factories.CertificateFactory.create(
            sid="067", certificate_type=certificate_type_c
        )

        # Setup good nomenclature
        root_cc = factories.GoodsNomenclatureFactory.create(
            sid="1000",
            item_id="1000000000",
            suffix="80",
            valid_between=DateTimeTZRange(START_TIME, None),
        )
        make_child(
            root_cc,
            sid="1100",
            item_id="1100000000",
            suffix="80",
            valid_between=DateTimeTZRange(START_TIME, None)
        )
        make_child(
            root_cc,
            sid="1200",
            item_id="1200000000",
            suffix="80",
            valid_between=DateTimeTZRange(START_TIME, None)
        )

        # Setup additional codes
        additional_code_type = factories.AdditionalCodeTypeFactory(
            sid="4",
            description="Restrictions",
        )
        factories.AdditionalCodeFactory(
            sid="1", code='013', type=additional_code_type
        )

        # Setup geographical area's
        factories.GeographicalAreaFactory.create(
            sid=335, area_id="IR", area_code=0
        )
        factories.GeographicalAreaFactory.create(
            sid=115, area_id="KP", area_code=0
        )

        # Footnotes
        ftn = factories.FootnoteTypeFactory.create(footnote_type_id="FN")
        factories.FootnoteFactory.create(footnote_id="001", footnote_type=ftn)
        factories.FootnoteFactory.create(footnote_id="002", footnote_type=ftn)

    @override_settings(DATA_IMPORT_USERNAME="Alice")
    def test_import_controls(self):
        """
        Expected output:
        -  add regulation C2100009 from 01/01/21

        """
        args = [
            fixture_path + "import_controls/new_measures.xlsx",
            fixture_path + "import_controls/existing_measures.xlsx",
        ]
        with output() as xml_output:
            opts = {
                "measure_sid": 1,
                "measure_condition_sid": 1,
                "transaction_id": 1,
                "envelope_id": 1,
                "output": xml_output.name,
                "new_measure_tabs": ['Iran (SAMLA)'],
                "old_skip_rows": 1,
            }
            call_command("import_import_controls", *args, **opts)
            expected_xml_output = fixture_path + "import_controls/expected_output.xml"
            diff = main.diff_files(
                xml_output,
                expected_xml_output,
            )
            assert not diff, f"Unexpected output: {diff}"


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

    @pytest.mark.xfail(reason="xlrd no longer supports xlsx format")
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

    @pytest.mark.xfail(reason="xlrd no longer supports xlsx format")
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
    @pytest.mark.xfail(reason="xlrd no longer supports xlsx format")
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
