import logging

from reference_documents.check.base import BaseRateCheck, BaseCheck
from reference_documents.check.base import BaseQuotaDefinitionCheck
from reference_documents.check.base import BaseOrderNumberCheck, BaseQuotaSuspensionCheck

# import additional checks
from reference_documents.check.ref_rates import RateExists  # noqa
from reference_documents.check.ref_quota_definitions import QuotaDefinitionExists  # noqa
from reference_documents.check.ref_order_numbers import OrderNumberChecks  # noqa
from reference_documents.check.ref_quota_suspensions import QuotaSuspensionExists  # noqa

from reference_documents.check.utils import Utils
from reference_documents.models import AlignmentReport, AlignmentReportStatus, RefQuotaSuspension, AlignmentReportCheckStatus
from reference_documents.models import AlignmentReportCheck
from reference_documents.models import ReferenceDocumentVersion

logger = logging.getLogger(__name__)


class Checks:
    def __init__(self, reference_document_version: ReferenceDocumentVersion):
        self.logger = logger
        self.reference_document_version = reference_document_version
        self.alignment_report = AlignmentReport.objects.create(
            reference_document_version=self.reference_document_version,
            status=AlignmentReportStatus.PENDING
        )

    @staticmethod
    def get_checks_for(check_class):
        return Utils().get_child_checks(check_class)

    @staticmethod
    def status_contains_failed_or_skipped(statuses):
        if AlignmentReportCheckStatus.FAIL in statuses or AlignmentReportCheckStatus.SKIPPED in statuses:
            return True
        return False

    def run(self):
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
        # except Exception as e:
        #     logger.error(e)
        #     logger.error('alignment check run errored')
        #     self.alignment_report.errored()
        #     self.alignment_report.save()

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
