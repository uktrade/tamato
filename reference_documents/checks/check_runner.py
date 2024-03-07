from reference_documents.checks.base import BasePreferentialQuotaCheck
from reference_documents.checks.base import BasePreferentialQuotaOrderNumberCheck
from reference_documents.checks.base import BasePreferentialRateCheck
from reference_documents.checks.preferential_quota_order_numbers import *  # noqa
from reference_documents.checks.preferential_quotas import *  # noqa
from reference_documents.checks.preferential_rates import *  # noqa
from reference_documents.checks.utils import Utils
from reference_documents.models import AlignmentReport
from reference_documents.models import AlignmentReportCheck
from reference_documents.models import ReferenceDocumentVersion


class Checks:
    def __init__(self, reference_document_version: ReferenceDocumentVersion):
        self.reference_document_version = reference_document_version
        self.alignment_report = AlignmentReport.objects.create(
            reference_document_version=self.reference_document_version,
        )

    @staticmethod
    def get_checks_for(check_class):
        return Utils().get_child_checks(check_class)

    def run(self):
        for check in Checks.get_checks_for(BasePreferentialRateCheck):
            for pref_rate in self.reference_document_version.preferential_rates.all():
                self.capture_check_result(check(pref_rate), pref_rate=pref_rate)

        for check in Checks.get_checks_for(BasePreferentialQuotaOrderNumberCheck):
            for (
                pref_quota_order_number
            ) in self.reference_document_version.preferential_quota_order_numbers.all():
                self.capture_check_result(
                    check(pref_quota_order_number),
                    pref_quota_order_number=pref_quota_order_number,
                )
                for sub_check in Checks.get_checks_for(BasePreferentialQuotaCheck):
                    for pref_quota in pref_quota_order_number.preferential_quotas.all():
                        self.capture_check_result(
                            sub_check(pref_quota),
                            pref_quota=pref_quota,
                        )

    def capture_check_result(
        self,
        check,
        pref_rate=None,
        pref_quota=None,
        pref_quota_order_number=None,
    ):
        status, message = check.run_check()

        kwargs = {
            "alignment_report": self.alignment_report,
            "check_name": check.__class__.__name__,
            "preferential_rate": pref_rate,
            "preferential_quota": pref_quota,
            "preferential_quota_order_number": pref_quota_order_number,
            "status": status,
            "message": message,
        }

        AlignmentReportCheck.objects.create(**kwargs)
