import os

import pytest

from importer.new_importer import NewImporter

pytestmark = pytest.mark.django_db


def get_test_xml_file(file_name):
    path_to_current_file = os.path.realpath(__file__)
    current_directory = os.path.split(path_to_current_file)[0]
    return os.path.join(current_directory, "test_files", file_name)


class TestNewImporter:
    def test_basic_import_additional_code_new_workbasket(self, superuser):
        file_to_import = get_test_xml_file("additional_code_CREATE.xml")

        importer = NewImporter(file_to_import, "import title", superuser.username)

        assert len(importer.issues()) == 0
        assert importer.status == "COMPLETED"
        assert importer.workbasket.transactions.count() == 1
        assert importer.workbasket.transactions.all()[0].tracked_models.count() == 2
        assert importer.workbasket.pk is not None
