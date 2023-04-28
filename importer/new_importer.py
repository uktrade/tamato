from typing import List

from bs4 import BeautifulSoup

from importer.new_parsers import TransactionParser


class NewImporter:
    """
    todo : write something meaningful
    """

    bs_taric3_file: BeautifulSoup
    raw_xml: str
    parsed_transactions: List[TransactionParser]

    def __init__(
        self,
        taric3_file: str,
        # username: str,
        # status: str,
        # partition_scheme_setting: str,
        # name: str,
        # split_codes: bool = False,
        # dependencies=None,
        # record_group: Sequence[str] = None
    ):
        self.parsed_transactions = []

        # Read xml into string
        with open(taric3_file, "r") as file:
            self.raw_xml = file.read()

        # load the taric3 file into memory, via beautiful soup
        self.bs_taric3_file = BeautifulSoup(self.raw_xml, "xml")

        # parse transactions
        self.parse()

        # validate, check dependencies and data
        self.validate()

        # if all good, commit to workbasket

    def print_stats(self, update_stats: dict):
        for key in update_stats.keys():
            print(f"{key} : {update_stats[key]}")

    def parse(self):
        transactions = self.bs_taric3_file.find_all("env:transaction")

        for transaction in transactions:
            self.parsed_transactions.append(TransactionParser(transaction))

    def stats(self):
        transaction_count = len(self.parsed_transactions)
        total_message_count = 0
        update_stats = {}

        for transaction in self.parsed_transactions:
            message_count = len(transaction.parsed_messages)

            total_message_count += message_count
            for taric_object in transaction.taric_objects:
                key = (
                    taric_object.xml_object_tag.replace(".", "_")
                    + "_"
                    + taric_object.update_type_name
                )
                if key in update_stats.keys():
                    update_stats[key] += 1
                else:
                    update_stats[key] = 1

        update_stats["transactions"] = transaction_count
        update_stats["messages"] = total_message_count

        return update_stats

    def validate(self):
        """Iterate through transactions and each taric model within, and verify
        progressively from the first transaction onwards, but not looking
        forwards for related objects, only each transaction backwards."""

        for transaction in self.parsed_transactions:
            for taric_object in transaction.taric_objects:
                print(taric_object.xml_object_tag)
                print(taric_object.child_links)
                print(taric_object.parent_links)
