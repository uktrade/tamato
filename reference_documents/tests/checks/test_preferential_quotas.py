from reference_documents.check.base import BaseQuotaDefinitionCheck
from reference_documents.models import AlignmentReportCheckStatus


class PreferentialQuotaExists(BaseQuotaDefinitionCheck):
    def run_check(self):
        if not self.order_number():
            message = f"FAIL - order number  not found"
            print(message)
            return AlignmentReportCheckStatus.FAIL, message

        if not self.geo_area():
            message = f"FAIL - geo area not found"
            print(message)
            return AlignmentReportCheckStatus.FAIL, message

        if not self.commodity_code():
            message = f"FAIL - commodity code not found"
            print(message)
            return AlignmentReportCheckStatus.FAIL, message

        if not self.quota_definition():
            message = f"FAIL - quota definition not found"
            print(message)
            return AlignmentReportCheckStatus.FAIL, message

        if not self.measure():
            message = (
                f"FAIL - measure(s) spanning whole quota definition period not found"
            )
            print(message)
            return AlignmentReportCheckStatus.FAIL, message
