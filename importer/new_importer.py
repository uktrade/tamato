from typing import List

from bs4 import BeautifulSoup

from importer.new_parsers import ModelLink
from importer.new_parsers import NewElementParser
from importer.new_parsers import TransactionParser


class NewImportIssueReportItem:
    """
    Class for in memory representation if an issue detected on import, the
    status may change during the process so this will not be committed until the
    import process is complete or has been found to have errors.

    params:
        object_type: str,
            String representation of the object type, as found in XML e.g. goods.nomenclature
        related_object_type: str,
            String representation of the related object type, as found in XML e.g. goods.nomenclature.description
        related_object_identity_keys: dict,
            Dictionary of identity names and values used to link the related object
        related_cache_key: str,
            The string expected to be used to cache the related object
        description: str,
            Description of the detected issue
    """

    def __init__(
        self,
        object_type: str,
        related_object_type: str,
        related_object_identity_keys: dict,
        description: str,
        issue_type: str = "ERROR",
    ):
        self.object_type = object_type
        self.related_object_type = related_object_type
        self.related_object_identity_keys = related_object_identity_keys
        self.description = description
        self.issue_type = issue_type

    def __str__(self):
        result = (
            f"{self.issue_type}: {self.description}\n"
            f"  {self.object_type} > {self.related_object_type}\n"
            f"  link_data: {self.related_object_identity_keys}"
        )
        return result

    def __repr__(self):
        return self.__str__()


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
        # import_name: str,
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

    def validate(self):
        """Iterate through transactions and each taric model within, and verify
        progressively from the first transaction onwards, but not looking
        forwards for related objects, only each transaction backwards."""

        for transaction in self.parsed_transactions:
            for parsed_message in transaction.parsed_messages:
                links_valid = True

                for link_data in parsed_message.taric_object.links() or []:
                    if not self._verify_link(parsed_message.taric_object, link_data):
                        links_valid = False

                parsed_message.taric_object.links_valid = links_valid

    def _verify_link(
        self,
        verifying_taric_object: NewElementParser,
        link_data: ModelLink,
    ):
        # verify either that the object exists on TAP or in current, previous transactions of current import
        kwargs = {}
        for field in link_data.fields:
            kwargs[field.object_field_name] = getattr(
                verifying_taric_object,
                field.parser_field_name,
            )

        # check database
        db_result = link_data.model.objects.latest_approved().filter(**kwargs)
        xml_result = []

        for transaction in self.parsed_transactions:
            for taric_object in transaction.taric_objects:
                # check transaction ID - only want to check ones that are less than current verifying object
                if taric_object.transaction_id > verifying_taric_object.transaction_id:
                    continue

                match = False
                if taric_object.xml_object_tag == link_data.xml_tag_name:
                    # ok we have matched the type - now check property
                    int_match = True
                    for field in link_data.fields:
                        if getattr(
                            verifying_taric_object,
                            field.parser_field_name,
                        ) != getattr(
                            taric_object,
                            field.object_field_name,
                        ):
                            int_match = False

                    if int_match:
                        match = True
                if match:
                    xml_result.append(taric_object)

        # verify that there is only one match, otherwise it's wrong
        record_match_count = db_result.count() + len(xml_result)
        if record_match_count == 1:
            return True
        elif record_match_count > 1:
            self.create_issue_report_item(
                verifying_taric_object,
                link_data,
                "Multiple matches for possible related taric object",
            )

            return False

        self.create_issue_report_item(
            verifying_taric_object,
            link_data,
            "No matches for possible related taric object",
        )

        return False

    def create_issue_report_item(
        self,
        target_taric_object: NewElementParser,
        link_data,
        description,
    ):
        identity_keys = {}

        for field in link_data.fields:
            identity_keys[field.object_field_name] = getattr(
                target_taric_object,
                field.parser_field_name,
            )

        report_item = NewImportIssueReportItem(
            target_taric_object.xml_object_tag,
            link_data.xml_tag_name,
            identity_keys,
            description,
        )

        target_taric_object.issues.append(report_item)

    def issues(self):
        issues = []
        for transaction in self.parsed_transactions:
            for message in transaction.parsed_messages:
                for issue in message.taric_object.issues:
                    issues.append(issue)

        return issues
