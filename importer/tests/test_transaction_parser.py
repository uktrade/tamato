import pytest
from bs4 import BeautifulSoup

from importer.new_parsers import TransactionParser

pytestmark = pytest.mark.django_db


class TestTransactionParser:
    def test_init(self):
        taric3_file = "./test_files/additional_code_CREATE.xml"
        raw_xml = ""

        # load bs4 file
        with open(taric3_file, "r") as file:
            raw_xml = file.read()

        bs_taric3_file = BeautifulSoup(raw_xml, "xml")

        transactions = bs_taric3_file.find_all("env:transaction")

        parsed_transaction = TransactionParser(transactions[0])

        assert len(transactions) == 1
        assert len(parsed_transaction.parsed_messages) == 2
