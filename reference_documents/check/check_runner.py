import logging

from reference_documents.check.base import BaseRateCheck, BaseCheck
from reference_documents.check.base import BaseQuotaDefinitionCheck
from reference_documents.check.base import BaseOrderNumberCheck, BaseQuotaSuspensionCheck

# import additional checks
from reference_documents.check.ref_rates import RateChecks  # noqa
from reference_documents.check.ref_quota_definitions import QuotaDefinitionChecks  # noqa
from reference_documents.check.ref_order_numbers import OrderNumberChecks  # noqa
from reference_documents.check.ref_quota_suspensions import QuotaSuspensionChecks  # noqa

from reference_documents.check.utils import Utils
from reference_documents.models import AlignmentReport, AlignmentReportStatus, RefQuotaSuspension, AlignmentReportCheckStatus
from reference_documents.models import AlignmentReportCheck
from reference_documents.models import ReferenceDocumentVersion

logger = logging.getLogger(__name__)


class Checks:
    """
    Class for running a sequence of checks against a reference document version.

    this class will run checks against all data in a reference document version, duty rate,
    order numbers, quota definitions, quota suspensions.

    The process is designed to only check child objects if the parent passes a check.
    If there is a failure or a skip from the parent check there is no point checking
    children - it will fail - so is marked as skipped.

    for example: if an order number is not on TAP subsequent quota definition checks are all marked as skipped
    and quota suspension checks are all marked as skipped.

    results are stored against the database and available via the UI under alignment checks.
    """
    def __init__(self, reference_document_version: ReferenceDocumentVersion):
        self.logger = logger
        self.reference_document_version = reference_document_version
        self.alignment_report = AlignmentReport.objects.create(
            reference_document_version=self.reference_document_version,
            status=AlignmentReportStatus.PENDING
        )

    @staticmethod
    def get_checks_for(check_class):
        """
        collects a list of classes that are subclasses of the provided check_class. Typically,
        this will be a base class for checks that other check classes inherit from.

        Args:
            check_class: a class that other classes inherit from - typically a base check class like BaseCheck

        Returns:
            list(check_classes): a list of classes that are subclasses if the provided check class
        """
        return Utils().get_child_checks(check_class)

    @staticmethod
    def status_contains_failed_or_skipped(statuses):
        """
        Used for determining if the child checks need to run or not, if statuses contains
        failed opr skipped statuses we don't want to run child checks, just skip them

        Args:
            statuses: list(AlignmentReportCheckStatus): A list of statuses we want to check

        Returns:
            boolean: True if the child checks pass or warn, False otherwise
        """
        if AlignmentReportCheckStatus.FAIL in statuses or AlignmentReportCheckStatus.SKIPPED in statuses:
            return True
        return False

    def run(self):
        """
        Sequentially runs checks for parent element progressing to child, grand child etc. and records the output
        of each check to the database.

        Returns:
            None

        """
        # try:
        logger.info('starting alignment check run')
        self.alignment_report.in_processing()
        self.alignment_report.save()

        # Preferential rate checks
        for ref_rate in self.reference_document_version.ref_rates.all():
            logger.info(f'starting checks for rate {ref_rate.commodity_code}')
            for ref_rate_check in Checks.get_checks_for(BaseRateCheck):
                logger.info(f'starting run: check {ref_rate_check.__class__.__name__}')
                self.capture_check_result(ref_rate_check(ref_rate), ref_rate=ref_rate)

        # Order number checks
        for ref_order_number in self.reference_document_version.ref_order_numbers.all():
            logger.info(f'starting checks for order number {ref_order_number.order_number}')
            order_number_check_statuses = []
            for order_number_check in Checks.get_checks_for(BaseOrderNumberCheck):
                logger.info(f'starting run: check {order_number_check.__class__.__name__}')
                order_number_check_statuses.append(
                    self.capture_check_result(
                        order_number_check(ref_order_number),
                        ref_order_number=ref_order_number,
                    )
                )

                # Quota definition checks
                for ref_quota_definition in ref_order_number.ref_quota_definitions.all():
                    logger.info(f'starting checks for quota definition {ref_quota_definition.commodity_code} for order number {ref_quota_definition.ref_order_number.order_number}')
                    pref_quota_check_statuses = []
                    for quota_definition_check in Checks.get_checks_for(BaseQuotaDefinitionCheck):
                        logger.info(f'starting run: check {quota_definition_check.__class__.__name__}')
                        pref_quota_check_statuses.append(self.capture_check_result(
                            quota_definition_check(ref_quota_definition),
                            ref_quota_definition=ref_quota_definition,
                            parent_has_failed_or_skipped_result=self.status_contains_failed_or_skipped(order_number_check_statuses)
                        ))

                        # Quota suspension checks
                        for ref_quota_suspension in RefQuotaSuspension.objects.all().filter(
                                ref_quota_definition=ref_quota_definition
                        ):
                            logger.info(f'starting checks for quota suspensions')
                            for quota_suspension_check in Checks.get_checks_for(BaseQuotaSuspensionCheck):
                                logger.info(f'starting run: check {quota_suspension_check.__class__.__name__}')
                                self.capture_check_result(
                                    quota_suspension_check(ref_quota_suspension),
                                    ref_quota_suspension=ref_quota_suspension,
                                    parent_has_failed_or_skipped_result=self.status_contains_failed_or_skipped(pref_quota_check_statuses)
                                )
                # Quota definition checks (range)
                for ref_quota_definition_range in ref_order_number.ref_quota_definition_ranges.all():
                    for ref_quota_definition in ref_quota_definition_range.dynamic_quota_definitions():
                        pref_quota_check_statuses = []
                        for quota_definition_check in Checks.get_checks_for(BaseQuotaDefinitionCheck):
                            pref_quota_check_statuses.append(
                                self.capture_check_result(
                                    quota_definition_check(ref_quota_definition),
                                    ref_quota_definition_range=ref_quota_definition_range,
                                    parent_has_failed_or_skipped_result=self.status_contains_failed_or_skipped(order_number_check_statuses)
                                )
                            )

                            # Quota suspension checks (range)
                            for quota_suspension_check in Checks.get_checks_for(BaseQuotaSuspensionCheck):
                                for ref_quota_suspension_range in ref_quota_definition_range.ref_quota_suspension_ranges.all():
                                    for pref_suspension in ref_quota_suspension_range.dynamic_quota_suspensions():
                                        self.capture_check_result(
                                            quota_suspension_check(pref_suspension),
                                            ref_quota_suspension_range=ref_quota_suspension_range,
                                            parent_has_failed_or_skipped_result=self.status_contains_failed_or_skipped(pref_quota_check_statuses)
                                        )
        self.alignment_report.complete()
        self.alignment_report.save()
        logger.info('finished alignment check run')

    def capture_check_result(
            self,
            check: BaseCheck,
            ref_rate=None,
            ref_quota_definition=None,
            ref_quota_definition_range=None,
            ref_order_number=None,
            ref_quota_suspension=None,
            ref_quota_suspension_range=None,
            parent_has_failed_or_skipped_result=None,
    ) -> AlignmentReportCheckStatus:
        """
        Captures the result if a single check and stores it in the database as a AlignmentReportCheck

        Args:
            check: Instance if check class BaseCheck or subclass
            ref_rate: RefRate if available or None
            ref_quota_definition: RefQuotaDefinition if available or None
            ref_quota_definition_range: RefQuotaDefinitionRange if available or None
            ref_order_number: RefOrderNumber if available or None
            ref_quota_suspension: RefQuotaSuspension if available or None
            ref_quota_suspension_range: RefQuotaSuspensionRange if available or None
            parent_has_failed_or_skipped_result: boolean

        Returns:
            AlignmentReportCheckStatus: the status of the check
        """
        if parent_has_failed_or_skipped_result:
            status = AlignmentReportCheckStatus.SKIPPED
            message = 'Check skipped due to parent check failure'
        else:
            status, message = check.run_check()

        kwargs = {
            "alignment_report": self.alignment_report,
            "check_name": check.name,
            "ref_rate": ref_rate,
            "ref_quota_definition": ref_quota_definition,
            "ref_quota_definition_range": ref_quota_definition_range,
            "ref_order_number": ref_order_number,
            "ref_quota_suspension": ref_quota_suspension,
            "ref_quota_suspension_range": ref_quota_suspension_range,
            "status": status,
            "message": message,
        }

        AlignmentReportCheck.objects.create(**kwargs)

        return status
