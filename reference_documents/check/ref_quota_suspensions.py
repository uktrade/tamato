from reference_documents.check.base import BaseQuotaSuspensionCheck
from reference_documents.models import AlignmentReportCheckStatus


class QuotaSuspensionExists(BaseQuotaSuspensionCheck):
    name = 'Preferential Suspension Exists'

    def run_check(self):
        # check if suspension exists - what criteria do we need?
        # comm code, order number and some dates
        if not self.tap_order_number():
            message = f"FAIL - order number not found"
            print(message)
            return AlignmentReportCheckStatus.FAIL, message

        if not self.quota_definition():
            message = f"FAIL - quota definitino not found"
            print(message)
            return AlignmentReportCheckStatus.FAIL, message

        if not self.suspension():
            message = f"FAIL - quota suspension not found"
            print(message)
            return AlignmentReportCheckStatus.FAIL, message
