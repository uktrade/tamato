from reference_documents.check.base import BaseQuotaDefinitionCheck
from reference_documents.models import AlignmentReportCheckStatus


class QuotaDefinitionExists(BaseQuotaDefinitionCheck):
    name = 'Preferential Quota Exists'

    def run_check(self):
        if not self.tap_order_number():
            message = f"FAIL - order number  not found"
            print(message)
            return AlignmentReportCheckStatus.FAIL, message

        elif not self.geo_area():
            message = f"FAIL - geo area not found"
            print(message)
            return AlignmentReportCheckStatus.FAIL, message

        elif not self.commodity_code():
            message = f"FAIL - commodity code not found"
            print(message)
            return AlignmentReportCheckStatus.FAIL, message

        elif not self.quota_definition():
            message = f"FAIL - quota definition not found"
            print(message)
            return AlignmentReportCheckStatus.FAIL, message

        elif not self.measures():
            message = (
                f"FAIL - measure(s) spanning whole quota definition period not found"
            )
            print(message)
            return AlignmentReportCheckStatus.FAIL, message
        else:
            return AlignmentReportCheckStatus.PASS, ''

