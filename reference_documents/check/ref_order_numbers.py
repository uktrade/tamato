from reference_documents.check.base import BaseOrderNumberCheck
from reference_documents.models import AlignmentReportCheckStatus


class OrderNumberChecks(BaseOrderNumberCheck):
    name = 'Order Number Exists'

    def run_check(self):
        # handle incomplete order number dates (from import)
        if self.ref_order_number.valid_between is None:
            message = f"order number {self.ref_order_number.order_number} cant be checked, no validity date range"
            print("FAIL", message)
            return AlignmentReportCheckStatus.FAIL, message
        # Verify that the order number exists in TAP
        elif not self.tap_order_number():
            message = f"order number not found matching {self.ref_order_number.order_number}"
            print("FAIL", message)
            return AlignmentReportCheckStatus.FAIL, message
        else:
            print(f"PASS - order number {self.tap_order_number()} found")
            return AlignmentReportCheckStatus.PASS, ""
