from typing import List

from bs4 import BeautifulSoup
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.db import transaction

from importer.models import BatchImportError
from importer.models import ImportBatch
from taric.models import Envelope
from taric_parsers.parsers.taric_parser import *
from workbaskets.models import WorkBasket


class TaricImporter:
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

    def find_parent_for_parser_object(self, taric_object: BaseTaricParser):
        if not taric_object.is_child_object():
            raise Exception(f"Only call this method on child objects")

        for parsed_transaction in self.parsed_transactions:
            for message in parsed_transaction.parsed_messages:
                if message.taric_object.model == taric_object.model:
                    if message.taric_object.is_child_object():
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
                    # We only need the parent to be present for creation, if it's an update it can be applied in isolation
                    if message.update_type != 1:
                        parent = self.find_parent_for_parser_object(
                            message.taric_object,
                        )
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
            report_item = ImportIssueReportItem(
                object_type=message.taric_object.xml_object_tag,
                related_object_type="None",
                related_object_identity_keys={},
                description=f"Database Integrity error, review related issues to determine what went wrong {e}",
                taric_change_type=message.update_type_name,
                object_details=str(message.taric_object),
                transaction_id=message.transaction_id,
            )

            message.taric_object.issues.append(report_item)

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

        for index, xml_transaction in enumerate(transactions):
            self.parsed_transactions.append(TransactionParser(xml_transaction, index))

    def find_child_objects(
        self,
        child_parser_class,
        parent: BaseTaricParser,
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
        child_parser: BaseTaricParser,
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

        for parsed_transaction in self.parsed_transactions:
            for parsed_message in parsed_transaction.parsed_messages:
                if (
                    parsed_message.taric_object.is_child_object()
                    and parsed_message.update_type == 3  # Create
                ):
                    parent_parser_class = ParserHelper.get_parser_by_model(
                        parsed_message.taric_object.__class__.model,
                    )
                    parent = self.find_parent(
                        parsed_message.taric_object,
                        parsed_transaction,
                    )

                    if parent is None:
                        report_item = ImportIssueReportItem(
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
                    # Check update type
                    self.validate_update_type_for(parsed_message, parsed_transaction)

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
                            parsed_transaction,
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
                                report_item = ImportIssueReportItem(
                                    parsed_message.taric_object.xml_object_tag,
                                    child_parser_class.xml_object_tag,
                                    {},
                                    f"Missing expected child object {child_parser_class.__name__}",
                                    taric_change_type=parsed_message.update_type_name,
                                    object_details=str(parsed_message.taric_object),
                                    transaction_id=parsed_message.transaction_id,
                                )

                                parsed_message.taric_object.issues.append(report_item)

    def validate_update_type_for(self, parsed_message, parsed_transaction):
        if parsed_message.update_type == 3:  # Create
            # Check if record exists for identity keys
            model_instances = (
                parsed_message.taric_object.__class__.model.objects.all().filter(
                    **parsed_message.taric_object.model_query_parameters()
                )
            )

            last_parsed_message_for_model = None

            for tmp_transaction in self.parsed_transactions:
                if parsed_transaction.index == tmp_transaction.index:
                    break  # done, don't want to process same transaction as the object we are looking at

                for message in tmp_transaction.parsed_messages:
                    # Check for match of identifying fields
                    if (
                        message.taric_object.model_query_parameters()
                        == parsed_message.taric_object.model_query_parameters()
                    ):
                        if type(message.taric_object) is type(
                            parsed_message.taric_object,
                        ):
                            # We have a match
                            last_parsed_message_for_model = message

            if last_parsed_message_for_model or model_instances.count() > 0:
                # Any scenario is invalid at this point, since we are dealing with a creation, raise issue

                report_item = ImportIssueReportItem(
                    parsed_message.taric_object.xml_object_tag,
                    "",
                    parsed_message.taric_object.model_query_parameters(),
                    f"Identity keys match existing object in database (checking all published and unpublished data)",
                    taric_change_type=parsed_message.update_type_name,
                    object_details=str(parsed_message.taric_object),
                    transaction_id=parsed_message.transaction_id,
                )

                parsed_message.taric_object.issues.append(report_item)

        if parsed_message.update_type == 1:
            if not parsed_message.taric_object.__class__.updates_allowed:
                report_item = ImportIssueReportItem(
                    parsed_message.taric_object.xml_object_tag,
                    "",
                    parsed_message.taric_object.model_query_parameters(),
                    f"Taric objects of type {parsed_message.taric_object.__class__.model.__name__} can't be updated",
                    taric_change_type=parsed_message.update_type_name,
                    object_details=str(parsed_message.taric_object),
                    transaction_id=parsed_message.transaction_id,
                )

                parsed_message.taric_object.issues.append(report_item)

            # Check if updated, deleted object exists, else raise issue
            model_instances = parsed_message.taric_object.__class__.model.objects.latest_approved().filter(
                **parsed_message.taric_object.model_query_parameters()
            )

            last_parsed_message_for_model = None

            for tmp_transaction in self.parsed_transactions:
                if parsed_transaction.index == tmp_transaction.index:
                    break  # done, don't want to process same transaction as the object we are looking at

                for message in tmp_transaction.parsed_messages:
                    # Check for match of identifying fields
                    if (
                        message.taric_object.model_query_parameters()
                        == parsed_message.taric_object.model_query_parameters()
                    ):
                        if type(message.taric_object) is type(
                            parsed_message.taric_object,
                        ):
                            # We have a match
                            last_parsed_message_for_model = message

            change_valid = True
            message = ""

            # If there are not any entries for this model, prior to this change : not valid
            if not last_parsed_message_for_model and model_instances.count() == 0:
                change_valid = False
                message = (
                    f"Identity keys do not match an existing object in database or import, cant apply update to a deleted or non existent object",
                )
            # If the model has been deleted previously in the same envelope : not valid
            elif (
                last_parsed_message_for_model
                and last_parsed_message_for_model.update_type == 2
            ):
                change_valid = False
                message = (
                    f"Identity keys match a previous message in this import that deletes this object",
                )

            if not change_valid:
                report_item = ImportIssueReportItem(
                    parsed_message.taric_object.xml_object_tag,
                    "",
                    parsed_message.taric_object.model_query_parameters(),
                    message,
                    taric_change_type=parsed_message.update_type_name,
                    object_details=str(parsed_message.taric_object),
                    transaction_id=parsed_message.transaction_id,
                )

                parsed_message.taric_object.issues.append(report_item)

        if parsed_message.update_type == 2:
            if not parsed_message.taric_object.__class__.deletes_allowed:
                msg = f"Taric objects of type {parsed_message.taric_object.__class__.model.__name__} can't be deleted"
                if parsed_message.taric_object.is_child_object:
                    msg = f"Children of Taric objects of type {parsed_message.taric_object.__class__.model.__name__} can't be deleted directly"

                report_item = ImportIssueReportItem(
                    parsed_message.taric_object.xml_object_tag,
                    "",
                    parsed_message.taric_object.model_query_parameters(),
                    msg,
                    taric_change_type=parsed_message.update_type_name,
                    object_details=str(parsed_message.taric_object),
                    transaction_id=parsed_message.transaction_id,
                )

                parsed_message.taric_object.issues.append(report_item)

            # Check if updated, deleted object exists, else raise issue
            model_instances = parsed_message.taric_object.__class__.model.objects.latest_approved().filter(
                **parsed_message.taric_object.model_query_parameters()
            )

            last_parsed_message_for_model = None

            for tmp_transaction in self.parsed_transactions:
                if parsed_transaction.index == tmp_transaction.index:
                    break  # done, don't want to process same transaction as the object we are looking at

                for message in tmp_transaction.parsed_messages:
                    # Check for match of identifying fields
                    if (
                        message.taric_object.model_query_parameters()
                        == parsed_message.taric_object.model_query_parameters()
                    ):
                        if type(message.taric_object) is type(
                            parsed_message.taric_object,
                        ):
                            # We have a match
                            last_parsed_message_for_model = message

            change_valid = True
            message = ""

            # If there are not any entries for this model, prior to this change : not valid
            if not last_parsed_message_for_model and model_instances.count() == 0:
                change_valid = False
                message = (
                    f"Identity keys do not match an existing object in database or import, cant delete non existent object",
                )
            # If the model has been deleted previously in the same envelope : not valid
            elif (
                last_parsed_message_for_model
                and last_parsed_message_for_model.update_type == 2
            ):
                change_valid = False
                message = (
                    f"Identity keys match a previous message in this import that deletes this object",
                )

            if not change_valid:
                report_item = ImportIssueReportItem(
                    parsed_message.taric_object.xml_object_tag,
                    "",
                    parsed_message.taric_object.model_query_parameters(),
                    message,
                    taric_change_type=parsed_message.update_type_name,
                    object_details=str(parsed_message.taric_object),
                    transaction_id=parsed_message.transaction_id,
                )

                parsed_message.taric_object.issues.append(report_item)

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
