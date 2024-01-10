import os

import pytest
from bs4 import BeautifulSoup

from taric_parsers.parsers.additional_code_parsers import (  # noqa
    AdditionalCodeDescriptionParserV2,
)
from taric_parsers.parsers.additional_code_parsers import AdditionalCodeParserV2  # noqa
from taric_parsers.parsers.additional_code_parsers import (  # noqa
    AdditionalCodeTypeParserV2,
)
from taric_parsers.parsers.additional_code_parsers import (  # noqa
    FootnoteAssociationAdditionalCodeParserV2,
)
from taric_parsers.parsers.taric_parser import TransactionParser

pytestmark = pytest.mark.django_db


def get_test_xml_file(file_name):
    path_to_current_file = os.path.realpath(__file__)
    current_directory = os.path.split(path_to_current_file)[0]
    return os.path.join(current_directory, "support", file_name)


@pytest.mark.importer_v2
class TestTransactionParser:
    def test_init(self):
        taric3_file = get_test_xml_file("additional_code_CREATE.xml")
        raw_xml = ""

        # load bs4 file
        with open(taric3_file, "r") as file:
            raw_xml = file.read()

        bs_taric3_file = BeautifulSoup(raw_xml, "xml")

        transactions = bs_taric3_file.find_all("env:transaction")

        parsed_transaction = TransactionParser(transactions[0], 1)

        assert len(transactions) == 1
        assert len(parsed_transaction.parsed_messages) == 3
