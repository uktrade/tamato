import os

import pytest

from taric_parsers.taric_xml_source import TaricXMLFileSource
from taric_parsers.taric_xml_source import TaricXMLSourceBase
from taric_parsers.taric_xml_source import TaricXMLStringSource

pytestmark = pytest.mark.django_db


@pytest.mark.new_importer
class TestTaricXMLSourceBase:
    def test_init(self):
        assert isinstance(TaricXMLSourceBase(), TaricXMLSourceBase)

    def test_get_xml_string(self):
        target_inst = TaricXMLSourceBase()
        with pytest.raises(Exception) as e:
            target_inst.get_xml_string()

        assert "Implement on child class" in str(e)


@pytest.mark.new_importer
class TestTaricXMLStringSource:
    def test_init(self):
        assert isinstance(TaricXMLStringSource("xml"), TaricXMLStringSource)

    def test_get_xml_string(self):
        target_inst = TaricXMLStringSource("xml")
        assert target_inst.get_xml_string() == "xml"


@pytest.mark.new_importer
class TestTaricXMLFileSource:
    def get_xml_file_path(self):
        path_to_current_file = os.path.realpath(__file__)
        current_directory = os.path.split(path_to_current_file)[0]
        file_path_to_read = os.path.join(
            current_directory,
            "support",
            "additional_code_CREATE.xml",
        )
        return file_path_to_read

    def test_init(self):
        assert isinstance(
            TaricXMLFileSource(self.get_xml_file_path()),
            TaricXMLFileSource,
        )

    def test_get_xml_string(self):
        target_inst = TaricXMLFileSource(self.get_xml_file_path())
        assert "some description" in target_inst.get_xml_string()
