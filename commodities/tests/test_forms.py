from os import path

from django.core.files.uploadedfile import SimpleUploadedFile

from commodities import forms

TEST_FILES_PATH = path.join(path.dirname(__file__), "test_files")


def test_import_form_invalid_envelope_id():
    upload_file = open(f"{TEST_FILES_PATH}/valid.xml", "rb")
    file_data = {
        "taric_file": SimpleUploadedFile(
            upload_file.name,
            upload_file.read(),
            content_type="text/xml",
        ),
    }
    form = forms.CommodityImportForm({}, file_data)

    assert form.is_valid()
