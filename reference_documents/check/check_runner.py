import logging

from reference_documents.check.base import BasePreferentialQuotaCheck, BaseCheck
from reference_documents.check.base import BasePreferentialQuotaOrderNumberCheck
from reference_documents.check.base import BasePreferentialRateCheck, BasePreferentialSuspensionCheck

# import additional checks
from reference_documents.check.ref_rates import MeasureExists  # noqa
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

    def run(self):
        try:
            logger.info('starting alignment check run')
            self.alignment_report.in_processing()
            self.alignment_report.save()

            # Preferential rate checks
            for ref_rate_check in Checks.get_checks_for(BasePreferentialRateCheck):
                logger.info(f'starting run: check {ref_rate_check.__class__.__name__}')
                for ref_rate in self.reference_document_version.ref_rates.all():
                    self.capture_check_result(ref_rate_check(ref_rate), ref_rate=ref_rate)

            # Order number checks
            for order_number_check in Checks.get_checks_for(BasePreferentialQuotaOrderNumberCheck):
                logger.info(f'starting run: check {order_number_check.__class__.__name__}')
                for ref_order_number in self.reference_document_version.ref_order_numbers.all():
                    order_number_check_status = self.capture_check_result(
                        order_number_check(ref_order_number),
                        ref_order_number=ref_order_number,
                    )
                    # Quota definition checks
                    for pref_quota_check in Checks.get_checks_for(BasePreferentialQuotaCheck):
                        for ref_quota_definition in ref_order_number.preferential_quotas.all():
                            pref_quota_check_status = self.capture_check_result(
                                pref_quota_check(ref_quota_definition),
                                ref_quota_definition=ref_quota_definition,
                                parent_check_status=order_number_check_status
                            )
                            # Quota suspension checks
                            for pref_suspension_check in Checks.get_checks_for(BasePreferentialSuspensionCheck):
                                for ref_quota_suspension in RefQuotaSuspension.objects.all().filter(
                                        ref_quota_definition=ref_quota_definition
                                ):
                                    self.capture_check_result(
                                        pref_suspension_check(ref_quota_suspension),
                                        ref_quota_suspension=ref_quota_suspension,
                                        parent_check_status=pref_quota_check_status
                                    )
                        # Quota definition checks (templated)
                        for ref_quota_definition_range in ref_order_number.ref_quota_suspension_ranges.all():
                            for ref_quota_definition in ref_quota_definition_range.dynamic_preferential_quotas():
                                pref_quota_check_status = self.capture_check_result(
                                    pref_quota_check(ref_quota_definition),
                                    ref_quota_definition_range=ref_quota_definition_range,
                                    parent_check_status=order_number_check_status
                                )

                                # Quota suspension checks (templated)
                                for pref_suspension_check in Checks.get_checks_for(BasePreferentialSuspensionCheck):
                                    for ref_quota_suspension_range in ref_quota_definition_range.preferential_quota_suspension_templates.all():
                                        for pref_suspension in ref_quota_suspension_range.dynamic_preferential_quota_suspensions():
                                            self.capture_check_result(
                                                pref_suspension_check(pref_suspension),
                                                ref_quota_suspension_range=ref_quota_suspension_range,
                                                parent_check_status=pref_quota_check_status
                                            )
            self.alignment_report.complete()
            self.alignment_report.save()
            logger.info('finished alignment check run')
        except Exception as e:
            logger.error(e)
            logger.error('alignment check run errored')
            self.alignment_report.errored()
            self.alignment_report.save()

    def capture_check_result(
            self,
            check: BaseCheck,
            ref_rate=None,
            ref_quota_definition=None,
            ref_quota_definition_range=None,
            ref_order_number=None,
            ref_quota_suspension=None,
            ref_quota_suspension_range=None,
            parent_check_status=None,
    ) -> AlignmentReportCheckStatus:
        if parent_check_status in [AlignmentReportCheckStatus.FAIL, AlignmentReportCheckStatus.SKIPPED]:
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
