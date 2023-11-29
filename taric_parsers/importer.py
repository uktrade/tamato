from typing import Generator
from typing import List
from typing import Optional

from bs4 import BeautifulSoup
from django.db import IntegrityError
from django.db import transaction

from common import validators
from common.models import Transaction
from common.validators import UpdateType
from importer.models import BatchImportError
from importer.models import ImportBatch
from importer.models import ImportIssueType
from taric.models import Envelope
from taric_parsers.parsers.additional_code_parsers import (  # noqa
    NewAdditionalCodeDescriptionParser,
)
from taric_parsers.parsers.additional_code_parsers import (  # noqa
    NewAdditionalCodeDescriptionPeriodParser,
)
from taric_parsers.parsers.additional_code_parsers import (  # noqa
    NewAdditionalCodeParser,
)
from taric_parsers.parsers.additional_code_parsers import (  # noqa
    NewAdditionalCodeTypeDescriptionParser,
)
from taric_parsers.parsers.additional_code_parsers import (  # noqa
    NewAdditionalCodeTypeParser,
)
from taric_parsers.parsers.additional_code_parsers import (  # noqa
    NewFootnoteAssociationAdditionalCodeParser,
)
from taric_parsers.parsers.certificate_parser import (  # noqa
    NewCertificateDescriptionParser,
)
from taric_parsers.parsers.certificate_parser import (  # noqa
    NewCertificateDescriptionPeriodParser,
)
from taric_parsers.parsers.certificate_parser import NewCertificateParser  # noqa
from taric_parsers.parsers.certificate_parser import (  # noqa
    NewCertificateTypeDescriptionParser,
)
from taric_parsers.parsers.certificate_parser import NewCertificateTypeParser  # noqa
from taric_parsers.parsers.commodity_parser import (  # noqa
    NewFootnoteAssociationGoodsNomenclatureParser,
)
from taric_parsers.parsers.commodity_parser import (  # noqa
    NewGoodsNomenclatureDescriptionParser,
)
from taric_parsers.parsers.commodity_parser import (  # noqa
    NewGoodsNomenclatureDescriptionPeriodParser,
)
from taric_parsers.parsers.commodity_parser import (  # noqa
    NewGoodsNomenclatureIndentParser,
)
from taric_parsers.parsers.commodity_parser import (  # noqa
    NewGoodsNomenclatureOriginParser,
)
from taric_parsers.parsers.commodity_parser import NewGoodsNomenclatureParser  # noqa
from taric_parsers.parsers.commodity_parser import (  # noqa
    NewGoodsNomenclatureSuccessorParser,
)
from taric_parsers.parsers.footnote_parser import NewFootnoteDescriptionParser  # noqa
from taric_parsers.parsers.footnote_parser import (  # noqa
    NewFootnoteDescriptionPeriodParser,
)
from taric_parsers.parsers.footnote_parser import NewFootnoteParser  # noqa
from taric_parsers.parsers.footnote_parser import (  # noqa
    NewFootnoteTypeDescriptionParser,
)
from taric_parsers.parsers.footnote_parser import NewFootnoteTypeParser  # noqa
from taric_parsers.parsers.geo_area_parser import (  # noqa
    NewGeographicalAreaDescriptionParser,
)
from taric_parsers.parsers.geo_area_parser import (  # noqa
    NewGeographicalAreaDescriptionPeriodParser,
)
from taric_parsers.parsers.geo_area_parser import NewGeographicalAreaParser  # noqa
from taric_parsers.parsers.geo_area_parser import (  # noqa
    NewGeographicalMembershipParser,
)
from taric_parsers.parsers.measure_parser import (  # noqa
    NewAdditionalCodeTypeMeasureTypeParser,
)
from taric_parsers.parsers.measure_parser import (  # noqa
    NewDutyExpressionDescriptionParser,
)
from taric_parsers.parsers.measure_parser import NewDutyExpressionParser  # noqa
from taric_parsers.parsers.measure_parser import (  # noqa
    NewFootnoteAssociationMeasureParser,
)
from taric_parsers.parsers.measure_parser import (  # noqa
    NewMeasureActionDescriptionParser,
)
from taric_parsers.parsers.measure_parser import NewMeasureActionParser  # noqa
from taric_parsers.parsers.measure_parser import NewMeasureComponentParser  # noqa
from taric_parsers.parsers.measure_parser import (  # noqa
    NewMeasureConditionCodeDescriptionParser,
)
from taric_parsers.parsers.measure_parser import NewMeasureConditionCodeParser  # noqa
from taric_parsers.parsers.measure_parser import (  # noqa
    NewMeasureConditionComponentParser,
)
from taric_parsers.parsers.measure_parser import NewMeasureConditionParser  # noqa
from taric_parsers.parsers.measure_parser import (  # noqa
    NewMeasureExcludedGeographicalAreaParser,
)
from taric_parsers.parsers.measure_parser import NewMeasurementParser  # noqa
from taric_parsers.parsers.measure_parser import (  # noqa
    NewMeasurementUnitDescriptionParser,
)
from taric_parsers.parsers.measure_parser import NewMeasurementUnitParser  # noqa
from taric_parsers.parsers.measure_parser import (  # noqa
    NewMeasurementUnitQualifierDescriptionParser,
)
from taric_parsers.parsers.measure_parser import (  # noqa
    NewMeasurementUnitQualifierParser,
)
from taric_parsers.parsers.measure_parser import NewMeasureParser  # noqa
from taric_parsers.parsers.measure_parser import NewMeasureTypeDescriptionParser  # noqa
from taric_parsers.parsers.measure_parser import NewMeasureTypeParser  # noqa
from taric_parsers.parsers.measure_parser import (  # noqa
    NewMeasureTypeSeriesDescriptionParser,
)
from taric_parsers.parsers.measure_parser import NewMeasureTypeSeriesParser  # noqa
from taric_parsers.parsers.measure_parser import (  # noqa
    NewMonetaryUnitDescriptionParser,
)
from taric_parsers.parsers.measure_parser import NewMonetaryUnitParser  # noqa
from taric_parsers.parsers.quota_parser import NewQuotaAssociationParser  # noqa
from taric_parsers.parsers.quota_parser import NewQuotaBalanceEventParser  # noqa
from taric_parsers.parsers.quota_parser import NewQuotaBlockingParser  # noqa
from taric_parsers.parsers.quota_parser import (  # noqa
    NewQuotaClosedAndTransferredEventParser,
)
from taric_parsers.parsers.quota_parser import NewQuotaCriticalEventParser  # noqa
from taric_parsers.parsers.quota_parser import NewQuotaDefinitionParser  # noqa
from taric_parsers.parsers.quota_parser import NewQuotaEventParser  # noqa
from taric_parsers.parsers.quota_parser import NewQuotaExhaustionEventParser  # noqa
from taric_parsers.parsers.quota_parser import (  # noqa
    NewQuotaOrderNumberOriginExclusionParser,
)
from taric_parsers.parsers.quota_parser import NewQuotaOrderNumberOriginParser  # noqa
from taric_parsers.parsers.quota_parser import NewQuotaOrderNumberParser  # noqa
from taric_parsers.parsers.quota_parser import NewQuotaReopeningEventParser  # noqa
from taric_parsers.parsers.quota_parser import NewQuotaSuspensionParser  # noqa
from taric_parsers.parsers.quota_parser import NewQuotaUnblockingEventParser  # noqa
from taric_parsers.parsers.quota_parser import NewQuotaUnsuspensionEventParser  # noqa
from taric_parsers.parsers.regulation_parser import NewBaseRegulationParser  # noqa
from taric_parsers.parsers.regulation_parser import (  # noqa
    NewFullTemporaryStopActionParser,
)
from taric_parsers.parsers.regulation_parser import (  # noqa
    NewFullTemporaryStopRegulationParser,
)
from taric_parsers.parsers.regulation_parser import (  # noqa
    NewModificationRegulationParser,
)
from taric_parsers.parsers.regulation_parser import (  # noqa
    NewRegulationGroupDescriptionParser,
)
from taric_parsers.parsers.regulation_parser import NewRegulationGroupParser  # noqa
from taric_parsers.parsers.regulation_parser import (  # noqa
    NewRegulationReplacementParser,
)
from taric_parsers.parsers.taric_parser import BaseTaricParser  # noqa
from taric_parsers.parsers.taric_parser import ImportIssueReportItem  # noqa
from taric_parsers.parsers.taric_parser import MessageParser  # noqa
from taric_parsers.parsers.taric_parser import ParserHelper  # noqa
from taric_parsers.parsers.taric_parser import TransactionParser  # noqa
from taric_parsers.taric_xml_source import TaricXMLSourceBase
from taric_parsers.tasks import import_chunk
from workbaskets.models import WorkBasket


class TaricImporter:
    """
    TARIC importer. This class is initialised with either a TARIC 3 file or a
    TARIC 3 XML string. Subsequently, the XML is parsed and objects in memory
    are created and validated.

    If issues with the import are identified, the issues are logged in the
    database against the import report. If the import has no issues the importer
    proceeds to commit the data to the database.
    """

    bs_taric3_file: BeautifulSoup
    raw_xml: str
    parsed_transactions: List[TransactionParser]

    def __init__(
        self,
        import_batch: ImportBatch,
        taric_xml_source: TaricXMLSourceBase,
        workbasket: WorkBasket,
    ):
        """
        TaricImporter initializer. This class imports TARIC data into the TAP
        database, or reports on data issues encountered.

        Args:
            import_batch: ImportBatch
                This object is used to link instances of ImportIssueReportItem
            taric_xml_source: TaricXMLSourceBase
                Path to a local xml file that should be imported.
            workbasket: Workbasket
                If importing to an existing workbasket this variable will be used, else a new workbasket will be created.
        """

        self.parsed_transactions = []
        self.raw_xml = taric_xml_source.get_xml_string()

        self.bs_taric3_file = BeautifulSoup(self.raw_xml, "xml")
        self.workbasket = workbasket
        self.import_batch = import_batch

    def process_import(self):
        # parse transactions
        self.parse()

        # validate, check dependencies and data
        self.validate()

        if self.can_save():
            self.populate_parent_attributes()
            self.commit_data()

        # Store issues against import
        for issue in self.issues():
            BatchImportError.create_from_import_issue_report_item(
                issue,
                self.import_batch,
            )

        return self.status

    def ordered_transactions_and_messages(
        self,
        up_to_transaction=None,
    ) -> Generator[TransactionParser, MessageParser, None]:
        """
        Returns TransactionParser, Message until att TransactionParsers have
        been iterated or the up_to_transaction matches the current transaction.

        Args:
            up_to_transaction: TransactionParser (optional)
                Only iterate up to the provided transaction, inclusive.

        Returns:
            Generator[TransactionParser, MessageParser] for all matching provided criteria
        """
        for parsed_transaction in self.parsed_transactions:
            for message in parsed_transaction.parsed_messages:
                yield transaction, message

            # note: breaks after iterating each MessageParser in transaction.
            if transaction == up_to_transaction:
                break

    def find_parent_for_parser_object(self, taric_object: BaseTaricParser):
        """
        Finds a parent object within the same import, matching the key identity
        fields to the child object.

        Args:
            taric_object: (required) BaseTaricParser, the child object we want to resolve the parent for.

        Returns:
            BaseTaricParser, The parsed object that matches identity fields and is not a child parser.
        Exception:
            Raised when there is no match for the parent object.
        """

        if not taric_object.is_child_object():
            raise Exception(f"Only call this method on child objects")

        for (
            parsed_transaction,
            parsed_message,
        ) in self.ordered_transactions_and_messages():
            possible_parent_taric_object = parsed_message.taric_object
            if (
                not possible_parent_taric_object.is_child_object()
                and possible_parent_taric_object.__class__.model
                == taric_object.__class__.model
            ):
                match = True

                for (
                    key,
                    value,
                ) in taric_object.get_identity_fields_and_values_for_parent().items():
                    if (
                        hasattr(possible_parent_taric_object, key)
                        and getattr(possible_parent_taric_object, key) != value
                    ):
                        match = False

                if match:
                    return possible_parent_taric_object

        raise Exception(f"No parent matched for {taric_object.__class__.__name__}")

    def populate_parent_attributes(self):
        """
        Populates parent attributes from child objects, generally this applies
        to description and description period objects, where in the database
        stores both parent and child in the same table.

        Returns:
            None, changes are applied to the instances of parser classes stored in memory.
        """
        # need to copy all child attributes to parent objects within the import only
        for (
            parsed_transaction,
            parsed_message,
        ) in self.ordered_transactions_and_messages():
            # skip if the update has been flagged as not to import changes
            if not parsed_message.taric_object.import_changes:
                continue

            if parsed_message.taric_object.is_child_object():
                # We only need the parent to be present for creation, if it's an update it can be applied in isolation
                if parsed_message.update_type != validators.UpdateType.UPDATE:
                    parent = self.find_parent_for_parser_object(
                        parsed_message.taric_object,
                    )
                    attributes = parsed_message.taric_object.model_attributes(
                        self.workbasket.transactions.last(),
                        False,
                    )
                    for attribute_key in attributes.keys():
                        setattr(parent, attribute_key, attributes[attribute_key])

    @transaction.atomic
    def commit_data(self):
        """
        Commit the import to the database, iterating through each parsed
        transaction and the parsed objects contained within.

        Returns:
            None
        """

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
                if not message.taric_object.import_changes:
                    continue

                if message.taric_object.can_save_to_model():
                    self.commit_changes_from_message(
                        message,
                        transaction_inst,
                    )

            transaction_order += 1

        if len(self.issues(ImportIssueType.ERROR)) > 0:
            transaction.set_rollback(True)

    def commit_changes_from_message(
        self,
        message: MessageParser,
        transaction: Transaction,
    ):
        """
        Commit the changes in a parsed message to the database.

        Args:
            message: (Required) MessageParser, The message being committed to the database.
            transaction: (Required) Transaction, The database transaction the changes are being committed to.

        Returns:
            None
        """
        try:
            if message.update_type == validators.UpdateType.UPDATE:  # Update
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

            elif message.update_type == validators.UpdateType.DELETE:  # Delete
                model_instances = message.taric_object.__class__.model.objects.approved_up_to_transaction(
                    transaction,
                ).filter(
                    **message.taric_object.model_query_parameters()
                )

                if model_instances.count() == 1:
                    # mark the model as deleted
                    model_instances.first().new_version(
                        transaction=transaction,
                        workbasket=transaction.workbasket,
                        update_type=message.taric_object.update_type,
                    )
                elif model_instances.count() != 1:
                    if model_instances.count() > 1:
                        msg = "Multiple models matching query detected, please review data and correct before proceeding with this import."
                    else:
                        msg = "No matches for this model detected in published data, please verify record exists before attempting a delete of the record"

                    self.create_import_issue(
                        message,
                        related_tag="self",
                        related_identity_keys=message.taric_object.model_query_parameters(),
                        issue_type=ImportIssueType.ERROR,
                        message=msg,
                    )

            elif message.update_type == validators.UpdateType.CREATE:  # Create
                message.taric_object.__class__.model.objects.create(
                    transaction=transaction,
                    **message.taric_object.model_attributes(
                        transaction,
                        include_non_taric_attributes=True,
                    ),
                )
        except IntegrityError as e:
            self.create_import_issue(
                message,
                "None",
                {},
                f"Database Integrity error, review related issues to determine what went wrong {e}",
            )

    @property
    def status(self):
        """
        Status of the import, indicating the types of warnings / errors
        encountered.

        Returns:
            str, string representation of the outcome of the import.
            - COMPLETED : Successful import, no issues or warnings detected
            - COMPLETED_WITH_WARNINGS : Successful import, but with warnings
            - FAILED : failed import, no data committed to the database. Issues recorded against the import.
        """
        if len(self.issues(ImportIssueType.ERROR)) > 0:
            return "FAILED"
        elif len(self.issues(ImportIssueType.WARNING)) > 0:
            return "COMPLETED_WITH_WARNINGS"
        else:
            return "COMPLETED"

    def can_save(self):
        """
        Indicates if the current import can be saved.
        Note: If warnings have been detected, the import can still be completed. The warnings will be available to review.

        Returns:
            boolean, indicating the state of the import, and its ability to save due to no issues being recorded.
        """

        if self.status != "FAILED":
            return True
        return False

    def parse(self):
        """
        Iterates XML transaction nodes, parses and creates parsed transaction
        instances. This populates self.parsed_transactions.

        Returns:
            None
        """
        transactions = self.bs_taric3_file.find_all("env:transaction")

        for index, xml_transaction in enumerate(transactions):
            self.parsed_transactions.append(TransactionParser(xml_transaction, index))

    def find_child_objects_in_import(
        self,
        child_parser_class,
        parent: BaseTaricParser,
        last_transaction: TransactionParser,
    ):
        """

        Args:
            child_parser_class: (required) BaseTaricParser Class, The class to search for.
            parent: : (required) BaseTaricParser, parent object that we are looking for children of
            last_transaction: (required) TransactionParser, The last transaction to check, and all preceding it.

        Returns:
            list of BaseTaricParser matching parent criteria
        """
        result = []

        for (
            parsed_transaction,
            parsed_message,
        ) in self.ordered_transactions_and_messages(last_transaction):
            if isinstance(parsed_message.taric_object, child_parser_class):
                # check identity fields
                if parsed_message.taric_object.is_child_for(parent):
                    result.append(parsed_message.taric_object)

        return result

    def find_parent_in_import(
        self,
        child_parser: BaseTaricParser,
        up_to_transaction: TransactionParser,
    ):
        """
        Will return the latest matching parent up to the provided transaction in
        the current import if it exists. If there is no match against the
        parent, None will be returned.

        Args:
            child_parser: (required) BaseTaricParser, The child parser instance.
            up_to_transaction: (required) TransactionParser, The transaction that contains the child object.

        Returns:
            Parent parser or None
        """

        parent = None
        for (
            parsed_transaction,
            parsed_message,
        ) in self.ordered_transactions_and_messages(up_to_transaction):
            potential_parent = parsed_message.taric_object
            # matching model and not child?
            if (
                not potential_parent.is_child_object()
                and potential_parent.model == child_parser.model
            ):
                # check key fields
                if child_parser.is_child_for(potential_parent):
                    parent = potential_parent

        return parent

    def create_import_issue(
        self,
        parsed_message,
        related_tag="",
        related_identity_keys=None,
        message="",
        issue_type=ImportIssueType.ERROR,
    ):
        """
        Creates an import issue that will be recorded against the database at
        the end of the import process regardless of the success or failure.

        Args:
            parsed_message: (required) MessageParser, Parsed message from the XML import
            related_tag: (optional) str, the XML tag for the parsed message
            related_identity_keys: (optional) dict, a dictionary of keys defining the identity of the object.
            message: (optional) str, A string describing the encountered issue / warning.
            issue_type: (optional) str, from choices BatchImportErrorIssueType.choices (ERROR, WARNING and INFORMATION)
        """

        if related_identity_keys is None:
            related_identity_keys = {}

        report_item = ImportIssueReportItem(
            parsed_message.taric_object.xml_object_tag,
            related_tag,
            related_identity_keys,
            message,
            object_update_type=parsed_message.update_type,
            object_details=str(parsed_message.taric_object),
            transaction_id=parsed_message.transaction_id,
            issue_type=issue_type,
        )

        parsed_message.taric_object.issues.append(report_item)

    def validate(self):
        """
        Iterate through transactions and each taric model within, and verify
        progressively from the first transaction onwards, but not looking
        forwards for related objects, only each transaction backwards.0.

        This method should raise import issues with missing data where the child
        object is not present

        Returns:
            None, any outoput is appended as sisues
        """

        for parsed_transaction in self.parsed_transactions:
            for parsed_message in parsed_transaction.parsed_messages:
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
                    object_matches = self.find_child_objects_in_import(
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
                        if not parsed_message.can_populate_child_attrs_from_history():
                            self.create_import_issue(
                                parsed_message,
                                child_parser_class.xml_object_tag,
                                {},
                                f"Missing expected child object {child_parser_class.__name__}",
                            )

    def validate_update_type_update(self, parsed_message, parsed_transaction):
        """
        Validates a single parsed message that is an UPDATE to a taric object,
        within a transaction and adds any detected issues as import issues
        (ImportIssueReportItem) that are later stored in BatchImportError
        objects, adn committed to the database.

        Args:
            parsed_message: MessageParser
                The message that requires validation
            parsed_transaction: TransactionParser
                The transaction that contains the message that requires validation

        Returns:
            None
        """
        if not parsed_message.taric_object.__class__.updates_allowed:
            self.create_import_issue(
                parsed_message,
                "",
                parsed_message.taric_object.model_query_parameters(),
                f"Taric objects of type {parsed_message.taric_object.__class__.model.__name__} can't be updated",
            )

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
                    if type(message.taric_object) is type(parsed_message.taric_object):
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
            and last_parsed_message_for_model.update_type
            == validators.UpdateType.DELETE
        ):
            change_valid = False
            message = (
                f"Identity keys match a previous message in this import that deletes this object",
            )

        if not change_valid:
            self.create_import_issue(
                parsed_message,
                "",
                parsed_message.taric_object.model_query_parameters(),
                message,
            )

    @staticmethod
    def find_change_in_parsed_transaction(
        parsed_transaction,
        parser_class,
        identity_fields,
    ) -> Optional[BaseTaricParser]:
        """
        Finds any changes to an object based on the parser class and the
        identity fields provided.

        Args:
            parsed_transaction: TransactionParser
                The parsed transaction containing messages to check
            parser_class:
                The class (child of BaseTaricParser) that we are searching for
            identity_fields: dict
                A dictionary of keys and values that are used to identify a parsed message of type (parser_clas)

        Returns:
            BaseTaricParser or child of : When a match is found
            None : When no match is found
        """
        for parsed_message in parsed_transaction.parsed_messages:
            if parsed_message.taric_object is parser_class:
                match = True

                for identity_field in identity_fields.keys():
                    if (
                        getattr(parsed_message.taric_object, identity_field)
                        != identity_fields[identity_field]
                    ):
                        match = False

                if match and len(identity_fields.keys()) > 0:
                    return parsed_message.taric_object

        return None

    def validate_update_type_delete(self, parsed_message, parsed_transaction):
        """
        Validates a single parsed message that is an DELETE to a taric object,
        within a transaction and adds any detected issues as import issues
        (ImportIssueReportItem) that are later stored in BatchImportError
        objects, adn committed to the database.

        Args:
            parsed_message: MessageParser
                The message that requires validation
            parsed_transaction: TransactionParser
                The transaction that contains the message that requires validation

        Returns:
            None
        """
        if not parsed_message.taric_object.__class__.deletes_allowed:
            if parsed_message.taric_object.is_child_object:
                # is the parent being deleted in the same transaction?
                if self.find_change_in_parsed_transaction(
                    parsed_transaction,
                    ParserHelper.get_parser_by_model(
                        parsed_message.taric_object.__class__.model,
                    ),
                    parsed_message.taric_object.get_identity_fields_and_values_for_parent(),
                ):
                    return

                parsed_message.taric_object.import_changes = False

                msg = f"Children of Taric objects of type {parsed_message.taric_object.__class__.model.__name__} can't be deleted directly. This change will not be imported."
                issue_type = ImportIssueType.WARNING
            else:
                msg = f"Taric objects of type {parsed_message.taric_object.__class__.model.__name__} can't be deleted"
                issue_type = ImportIssueType.ERROR

            self.create_import_issue(
                parsed_message,
                "",
                parsed_message.taric_object.model_query_parameters(),
                msg,
                issue_type,
            )

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
                    if type(message.taric_object) is type(parsed_message.taric_object):
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
            and last_parsed_message_for_model.update_type
            == validators.UpdateType.DELETE
        ):
            change_valid = False
            message = (
                f"Identity keys match a previous message in this import that deletes this object",
            )

        if not change_valid:
            self.create_import_issue(
                parsed_message,
                "",
                parsed_message.taric_object.model_query_parameters(),
                message,
            )

    def validate_update_type_create(self, parsed_message, parsed_transaction):
        """
        Validates a single parsed message that is an CREATE to a taric object,
        within a transaction and adds any detected issues as import issues
        (ImportIssueReportItem) that are later stored in BatchImportError
        objects, adn committed to the database.

        Args:
            parsed_message: MessageParser
                The message that requires validation
            parsed_transaction: TransactionParser
                The transaction that contains the message that requires validation

        Returns:
            None
        """
        if parsed_message.taric_object.is_child_object():
            parent_parser_class = ParserHelper.get_parser_by_model(
                parsed_message.taric_object.__class__.model,
            )
            parent = self.find_parent_in_import(
                parsed_message.taric_object,
                parsed_transaction,
            )

            if parent is None:
                self.create_import_issue(
                    parsed_message,
                    parent_parser_class.xml_object_tag,
                    parsed_message.taric_object.get_identity_fields_and_values_for_parent(),
                    f"Missing expected parent object {parent_parser_class.__name__}",
                )

            return None

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

        # Check if record exists for identity keys
        model_instances = (
            parsed_message.taric_object.__class__.model.objects.all().filter(
                **parsed_message.taric_object.model_query_parameters()
            )
        )

        # check for deletes
        create_issue = False
        if not parsed_message.taric_object.skip_identity_check:
            if (
                model_instances.count() > 0
                and model_instances.last().update_type != UpdateType.DELETE
            ):
                create_issue = True
            elif (
                last_parsed_message_for_model
                and last_parsed_message_for_model.update_type != UpdateType.DELETE
            ):
                create_issue = True

            if create_issue:
                self.create_import_issue(
                    parsed_message,
                    "",
                    parsed_message.taric_object.model_query_parameters(),
                    f"Identity keys match existing non-deleted object in database (checking all published and unpublished data)",
                )

    def validate_update_type_for(self, parsed_message, parsed_transaction):
        """
        Determines the appropriate method to apply validation for a
        MessageParser instance.

        Args:
            parsed_message: MessageParser
                The instance we want to validate
            parsed_transaction: TransactionParser
                The transaction that contains the MessageParser instance

        Returns:
            None
        """
        if parsed_message.update_type == validators.UpdateType.CREATE:  # Create
            self.validate_update_type_create(parsed_message, parsed_transaction)
        if parsed_message.update_type == validators.UpdateType.UPDATE:  # Update
            self.validate_update_type_update(parsed_message, parsed_transaction)
        if parsed_message.update_type == validators.UpdateType.DELETE:  # Delete
            self.validate_update_type_delete(parsed_message, parsed_transaction)

    def issues(self, filter_by_issue_type: str = None) -> List[ImportIssueReportItem]:
        """
        Get issues identified during import.

        Args:
            filter_by_issue_type: (optional) str, either ERROR or WARNING

        Returns:
            list[ImportIssueReportItem], recorded issues during import
        """
        issues = []
        for parsed_transaction in self.parsed_transactions:
            for message in parsed_transaction.parsed_messages:
                for issue in message.taric_object.issues:
                    if filter_by_issue_type:
                        if issue.issue_type == filter_by_issue_type:
                            issues.append(issue)
                    else:
                        issues.append(issue)

        return issues


def run_batch(
    batch_id: int,
    partition_scheme_setting: str,
    username: str,
    workbasket_id: str = None,
):
    import_batch = ImportBatch.objects.get(pk=batch_id)

    import_chunk.delay(
        chunk_pk=import_batch.chunks.first().pk,
        workbasket_id=workbasket_id,
        partition_scheme_setting=partition_scheme_setting,
        username=username,
    )
