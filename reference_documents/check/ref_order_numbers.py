from reference_documents.check.base import BaseOrderNumberCheck
from reference_documents.models import AlignmentReportCheckStatus


class OrderNumberChecks(BaseOrderNumberCheck):
    """Class defining the check process for a reference document order number
    (RefOrderNumber)"""

    name = "Order number checks"

    def run_check(self):
        """
        Runs order number checks between a reference document defined order
        number and TAP data.

        Returns:
            AlignmentReportCheckStatus: status based on the result of the check (pass, warning, fail, skip)
            string: corresponding message for the status.
        """
        # handle incomplete order number dates (from import)
        if self.ref_order_number.valid_between is None:
            message = f"order number {self.ref_order_number.order_number} cant be checked, no validity date range provided on reference document data"
            print("FAIL", message)
            return AlignmentReportCheckStatus.FAIL, message
        # Verify that the order number exists in TAP
        elif not self.tap_order_number():
            message = f"order number not found matching {self.ref_order_number.order_number} validity {self.ref_order_number.valid_between}"
            print("FAIL", message)
            return AlignmentReportCheckStatus.FAIL, message
        else:
            print(
                f"PASS - order number {self.tap_order_number()} with validity {self.ref_order_number.valid_between} matched",
            )
            return AlignmentReportCheckStatus.PASS, ""
