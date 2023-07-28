import os

import pytest
from bs4 import BeautifulSoup

from importer.new_parsers import TransactionParser

pytestmark = pytest.mark.django_db


def get_test_xml_file(file_name):
    path_to_current_file = os.path.realpath(__file__)
    current_directory = os.path.split(path_to_current_file)[0]
    return os.path.join(current_directory, "test_files", file_name)


class TestTransactionParser:
    def test_init(self):
        taric3_file = get_test_xml_file("additional_code_CREATE.xml")
        raw_xml = ""

        # load bs4 file
        with open(taric3_file, "r") as file:
            raw_xml = file.read()

        bs_taric3_file = BeautifulSoup(raw_xml, "xml")

        transactions = bs_taric3_file.find_all("env:transaction")

        parsed_transaction = TransactionParser(transactions[0])

        assert len(transactions) == 1
        assert len(parsed_transaction.parsed_messages) == 2
