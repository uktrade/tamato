from reference_documents.check.base import BasePreferentialSuspensionCheck
from reference_documents.models import AlignmentReportCheckStatus


class QuotaSuspensionExists(BasePreferentialSuspensionCheck):
    name = 'Preferential Suspension Exists'

    def run_check(self):
        # check if suspension exists - what criteria do we need?
        # comm code, order number and some dates
        if not self.order_number():
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
