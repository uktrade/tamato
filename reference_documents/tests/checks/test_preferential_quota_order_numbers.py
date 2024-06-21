from reference_documents.check.base import BaseOrderNumberCheck
from reference_documents.models import AlignmentReportCheckStatus


class OrderNumberExists(BaseOrderNumberCheck):
    def run_check(self):
        if not self.order_number():
            message = f"order number not found"
            print("FAIL", message)
            return AlignmentReportCheckStatus.FAIL, message
        else:
            print(f"PASS - order number {self.order_number()} found")
            return AlignmentReportCheckStatus.PASS, ""
