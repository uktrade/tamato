import pytest

from common.tests.util import preload_import

pytestmark = pytest.mark.django_db


@pytest.mark.importer_v2
class TestForGenericImportErrors:
    def test_correctly_raises_error_when_create_for_existing_sid(self):
        preload_import("additional_code_CREATE.xml", __file__, True)
        importer = preload_import("additional_code_second_CREATE.xml", __file__)

        assert len(importer.issues()) == 1

        assert (
            "ERROR: Identity keys match existing non-deleted object in database (checking all published and unpublished data)"
            in str(importer.issues()[0])
        )
        assert "additional.code >" in str(importer.issues()[0])
        assert (
            "{"
            "'type': 'AdditionalcodeType 5: some description', "
            "'update_type': 3, "
            "'sid': 1, "
            "'code': '3', "
            "'valid_between': {'start': '2021-01-01', 'end': 'None'}}"
        ) in str(importer.issues()[0])

    def test_correctly_raises_error_when_update_for_non_existing_sid(self):
        importer = preload_import("additional_code_UPDATE.xml", __file__)

        assert len(importer.issues()) == 1

        # assert "Missing expected linked object NewAdditionalCodeTypeParser" in str(importer.issues()[0])
        # assert "link_data: {'sid': '5'}" in str(importer.issues()[0])

        assert "Identity keys do not match an existing object" in str(
            importer.issues()[0],
        )
        assert "additional.code >" in str(importer.issues()[0])
        assert "link_data: {'sid': 1}" in str(importer.issues()[0])
