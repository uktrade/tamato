from reference_documents.check.base import BaseQuotaSuspensionCheck
from reference_documents.models import AlignmentReportCheckStatus


class QuotaSuspensionExists(BaseQuotaSuspensionCheck):
    name = 'Preferential Suspension Exists'

    def run_check(self):
        if not self.tap_suspension():
            message = f"FAIL - quota suspension not found"
            print(message)
            return AlignmentReportCheckStatus.FAIL, message
        else:
            return AlignmentReportCheckStatus.PASS, ""
