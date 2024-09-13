from reference_documents.check.base import BaseQuotaSuspensionCheck
from reference_documents.models import AlignmentReportCheckStatus


class QuotaSuspensionChecks(BaseQuotaSuspensionCheck):
    """
    Class defining the check process for a reference document quota suspension (RefQuotaSuspension)
    """
    name = 'Quota suspension checks'

    def run_check(self):
        """
        Runs quota suspension checks between a reference document defined quota suspension and TAP data

        Returns:
            AlignmentReportCheckStatus: status based on the result of the check (pass, warning, fail, skip)
            string: corresponding message for the status.
        """
        if not self.tap_suspension():
            message = f"FAIL - quota suspension not found"
            print(message)
            return AlignmentReportCheckStatus.FAIL, message
        else:
            return AlignmentReportCheckStatus.PASS, ""
