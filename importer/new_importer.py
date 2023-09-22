from typing import List

from bs4 import BeautifulSoup
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.db import transaction

from common.models import Transaction
from importer.models import BatchImportError
from importer.models import ImportBatch
from importer.new_importer_issue import NewImportIssueReportItem
from importer.new_parser_model_links import ModelLink
from importer.new_parsers import MessageParser
from importer.new_parsers import NewElementParser
from importer.new_parsers import ParserHelper
from importer.new_parsers import TransactionParser
from taric.models import Envelope
from workbaskets.models import WorkBasket


class NewImporter:
    """
    todo : write something meaningful
    """

    bs_taric3_file: BeautifulSoup
    raw_xml: str
    parsed_transactions: List[TransactionParser]

    def __init__(
        self,
        import_batch: ImportBatch,
        taric3_file: str = None,
        taric3_xml_string: str = None,
        import_title: str = None,
        author_username: str = None,
        workbasket: WorkBasket = None,
    ):
        # Guard Clauses
        if not workbasket:
            if not import_title:
                raise Exception(
                    "Import title is required when no workbasket is provided",
                )
            elif not author_username:
                raise Exception(
                    "Author username is required when no workbasket is provided",
                )

        if not taric3_file and not taric3_xml_string:
            raise Exception(
                "No valid source provided, either taric3_file or taric3_xml_string need to be populated",
            )

        if taric3_xml_string and taric3_file:
            raise Exception(
                "Multiple valid source provided, either taric3_file or taric3_xml_string need to be populated, pick one",
            )

        self.parsed_transactions = []

        if taric3_xml_string:
            self.raw_xml = taric3_xml_string
        else:
            # Read xml into string
            with open(taric3_file, "r") as file:
                self.raw_xml = file.read()

        # load the taric3 file into memory, via beautiful soup
        self.bs_taric3_file = BeautifulSoup(self.raw_xml, "xml")

        # if all good, commit to workbasket
        if workbasket is None:
            author = User.objects.get(username=author_username)
            self.workbasket = WorkBasket(title=import_title, author=author)
            self.workbasket.save()
        else:
            self.workbasket = workbasket

        # parse transactions
        self.parse()

        # validate, check dependencies and data
        self.validate()

        # reorder models within a transaction to process the children

        if self.can_save():
            self.populate_parent_attributes()
            self.commit_data()

        # Store issues against import
        for issue in self.issues():
            BatchImportError.create_from_import_issue_report_item(issue, import_batch)

        return

    def find_parent_for_parser_object(self, taric_object: NewElementParser):
        if not taric_object.is_child_object():
            raise Exception(f"Only call this method on child objects")

        for parsed_transaction in self.parsed_transactions:
            for message in parsed_transaction.parsed_messages:
                if message.taric_object.model == taric_object.model:
                    if not message.taric_object.is_child_object():
                        parent = self.find_parent_object_matching_fields(
                            taric_object.__class__.model,
                            taric_object.get_identity_fields_and_values_for_parent(),
                        )

                        if parent:
                            return parent

        raise Exception(f"No parent matched for {taric_object.__class__.__name__}")

    def find_parent_object_matching_fields(self, model, fields: dict):
        for parsed_transaction in self.parsed_transactions:
            for message in parsed_transaction.parsed_messages:
                taric_object = message.taric_object
                if (
                    not taric_object.is_child_object()
                    and taric_object.__class__.model == model
                ):
                    match = True

                    for field in fields:
                        if (
                            hasattr(taric_object, field)
                            and getattr(taric_object, field) != fields[field]
                        ):
                            match = False

                    if match:
                        return taric_object

        raise Exception(f"No match for {model.__name__} using : {fields}")

    def populate_parent_attributes(self):
        # need to copy all child attributes to parent objects within the import only
        for parsed_transaction in self.parsed_transactions:
            for message in parsed_transaction.parsed_messages:
                if message.taric_object.is_child_object():
                    parent = self.find_parent_for_parser_object(message.taric_object)
                    attributes = message.taric_object.model_attributes(
                        self.workbasket.transactions.last(),
                        False,
                    )
                    for attribute_key in attributes.keys():
                        setattr(parent, attribute_key, attributes[attribute_key])

    @transaction.atomic
    def commit_data(self):
        envelope = Envelope.new_envelope()

        transaction_order = 1
        for parsed_transaction in self.parsed_transactions:
            # create transaction
            transaction_inst = Transaction.objects.create(
                composite_key=f"{envelope.envelope_id}{transaction_order}",
                workbasket=self.workbasket,
                order=transaction_order,
            )

            for message in parsed_transaction.parsed_messages:
                if message.taric_object.can_save_to_model():
                    self.commit_changes_from_message(
                        message,
                        transaction_inst,
                    )

            transaction_order += 1

        if len(self.issues("ERROR")) > 0:
            transaction.set_rollback(True)

    def commit_changes_from_message(
        self,
        message: MessageParser,
        transaction: Transaction,
    ):
        try:
            if message.update_type == 1:  # Update
                # find model based on identity key
                model_instance = (
                    message.taric_object.__class__.model.objects.approved_up_to_transaction(
                        transaction,
                    )
                    .filter(**message.taric_object.model_query_parameters())
                    .last()
                )

                # update model with all attributes from model
                model_instance.new_version(
                    transaction=transaction,
                    workbasket=transaction.workbasket,
                    **message.taric_object.model_attributes(transaction),
                )

            elif message.update_type == 2:  # Delete
                model_instance = message.taric_object.__class__.model.objects.approved_up_to_transaction(
                    transaction,
                ).get(
                    **message.taric_object.model_query_parameters()
                )

                # mark the model as deleted
                model_instance.new_version(
                    transaction=transaction,
                    workbasket=transaction.workbasket,
                    update_type=message.taric_object.update_type,
                )

            elif message.update_type == 3:  # Create
                message.taric_object.__class__.model.objects.create(
                    transaction=transaction,
                    **message.taric_object.model_attributes(
                        transaction,
                        include_non_taric_attributes=True,
                    ),
                )
        except IntegrityError as e:
            report_item = NewImportIssueReportItem(
                object_type=message.taric_object.xml_object_tag,
                related_object_type="None",
                related_object_identity_keys={},
                description=f"Database Integrity error, review related issues to determine what went wrong {e}",
                taric_change_type=message.update_type_name,
                object_details=str(message.taric_object),
                transaction_id=message.transaction_id,
            )

            message.taric_object.issues.append(report_item)

    def find_object_in_import(
        self,
        current_transaction,
        identity_fields: dict,
        object_type,
    ):
        match = None

        for transaction in self.parsed_transactions:
            for message in transaction.parsed_messages:
                if message.object_type == object_type:
                    # check keys
                    key_match = True
                    for key in identity_fields.keys():
                        if getattr(message.taric_object, key) != identity_fields[key]:
                            key_match = False

                    if key_match:
                        return message.taric_object

        return match

    def print_stats(self, update_stats: dict):
        for key in update_stats.keys():
            print(f"{key} : {update_stats[key]}")

    @property
    def status(self):
        if len(self.issues("ERROR")) > 0:
            return "FAILED"
        elif len(self.issues("WARNING")) > 0:
            return "COMPLETED_WITH_WARNINGS"
        else:
            return "COMPLETED"

    def can_save(self):
        if self.status != "FAILED":
            return True
        return False

    def parse(self):
        transactions = self.bs_taric3_file.find_all("env:transaction")

        for transaction in transactions:
            self.parsed_transactions.append(TransactionParser(transaction))

    def find_child_objects(
        self,
        child_parser_class,
        parent: NewElementParser,
        last_transaction: TransactionParser,
    ):
        result = []

        processed_last_transaction = False
        for parsed_transaction in self.parsed_transactions:
            if processed_last_transaction:
                break

            for parsed_message in parsed_transaction.parsed_messages:
                if isinstance(parsed_message.taric_object, child_parser_class):
                    # check identity fields
                    if parsed_message.taric_object.is_child_for(parent):
                        result.append(parsed_message.taric_object)

            if transaction == last_transaction:
                processed_last_transaction = True

        return result

    def find_parent(
        self,
        child_parser: NewElementParser,
        up_to_transaction: TransactionParser,
    ):
        # will return the last matching parent up to the provided transaction
        parent = None

        matched_transaction = None
        for transaction in self.parsed_transactions:
            # skip once matched transaction is processed
            if matched_transaction:
                continue

            for parsed_message in transaction.parsed_messages:
                potential_parent = parsed_message.taric_object
                # matching model and not child?
                if (
                    not potential_parent.is_child_object()
                    and potential_parent.model == child_parser.model
                ):
                    # check key fields
                    if child_parser.is_child_for(potential_parent):
                        parent = potential_parent

            if transaction == up_to_transaction:
                matched_transaction = transaction

        return parent

    def validate(self):
        """
        Iterate through transactions and each taric model within, and verify
        progressively from the first transaction onwards, but not looking
        forwards for related objects, only each transaction backwards.0.

        This method should raise import issues with missing data where the child
        object is not present
        """

        for transaction in self.parsed_transactions:
            for parsed_message in transaction.parsed_messages:
                if parsed_message.taric_object.is_child_object():
                    parent_parser_class = ParserHelper.get_parser_by_model(
                        parsed_message.taric_object.__class__.model,
                    )
                    parent = self.find_parent(parsed_message.taric_object, transaction)

                    if parent is None:
                        report_item = NewImportIssueReportItem(
                            parsed_message.taric_object.xml_object_tag,
                            parent_parser_class.xml_object_tag,
                            parsed_message.taric_object.get_identity_fields_and_values_for_parent(),
                            f"Missing expected parent object {parent_parser_class.__name__}",
                            taric_change_type=parsed_message.update_type_name,
                            object_details=str(parsed_message.taric_object),
                            transaction_id=parsed_message.transaction_id,
                        )

                        parsed_message.taric_object.issues.append(report_item)
                else:
                    # get the child models
                    child_parser_classes = ParserHelper.get_child_parsers(
                        parsed_message.taric_object,
                    )

                    # No child classes, we are good to go here
                    if len(child_parser_classes) == 0:
                        continue

                    # verify if a child of these types, linked to the current object exist in previous / current
                    # transactions
                    child_matches = {}
                    for child_parser_class in child_parser_classes:
                        object_matches = self.find_child_objects(
                            child_parser_class,
                            parsed_message.taric_object,
                            transaction,
                        )
                        for object_match in object_matches:
                            if object_match.__class__.__name__ in child_matches.keys():
                                child_matches[object_match.__class__.__name__] += 1
                            else:
                                child_matches[object_match.__class__.__name__] = 1

                    for child_parser_class in child_parser_classes:
                        if child_parser_class.__name__ not in child_matches.keys():
                            # This is where description periods can inherit from last create / update if the parsed message is an update to an existing object
                            if not parsed_message.can_populate_child_attrs_from_history(
                                child_parser_class,
                            ):
                                report_item = NewImportIssueReportItem(
                                    parsed_message.taric_object.xml_object_tag,
                                    child_parser_class.xml_object_tag,
                                    {},
                                    f"Missing expected child object {child_parser_class.__name__}",
                                    taric_change_type=parsed_message.update_type_name,
                                    object_details=str(parsed_message.taric_object),
                                    transaction_id=parsed_message.transaction_id,
                                )

                                parsed_message.taric_object.issues.append(report_item)

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
            taric_change_type=target_taric_object.update_type_name,
            object_details=str(target_taric_object),
            transaction_id=target_taric_object.transaction_id,
        )

        target_taric_object.issues.append(report_item)

    def issues(self, filter_by_issue_type: str = None):
        issues = []
        for transaction in self.parsed_transactions:
            for message in transaction.parsed_messages:
                for issue in message.taric_object.issues:
                    if filter_by_issue_type:
                        if issue.issue_type == filter_by_issue_type:
                            issues.append(issue)
                    else:
                        issues.append(issue)

        return issues
