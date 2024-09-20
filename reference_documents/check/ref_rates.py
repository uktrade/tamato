from reference_documents.check.base import BaseRateCheck
from reference_documents.models import AlignmentReportCheckStatus


class RateChecks(BaseRateCheck):
    """Class defining the check process for a reference document rate
    (RefRate)"""

    name = "Rate checks"

    def run_check(self):
        """
        Runs rate checks between a reference document defined rate and TAP data.

        Returns:
            AlignmentReportCheckStatus: status based on the result of the check (pass, warning, fail, skip)
            string: corresponding message for the status.
        """
        # comm code live on EIF date
        if not self.tap_comm_code():
            message = f"{self.ref_rate.commodity_code} {self.tap_geo_area_description()} comm code not live"
            print("FAIL", message)
            return AlignmentReportCheckStatus.FAIL, message

        # query measures
        measures = self.tap_related_measures()

        # this is ok - there is a single measure matching the expected query
        if len(measures) == 1:
            return AlignmentReportCheckStatus.PASS, ""

        # this is not inline with expected measures presence - check comm code children
        elif len(measures) == 0:
            # check 1 level down for presence of measures
            match = self.tap_recursive_comm_code_check(
                self.get_snapshot(),
                self.ref_rate.commodity_code,
                80,
            )

            message = f"{self.tap_comm_code()} : "

            if match:
                message += f"matched with children"
                print("PASS", message)

                return AlignmentReportCheckStatus.PASS, message
            else:
                message += f"no expected measures found on good code or children"
                print("FAIL", message)

                return AlignmentReportCheckStatus.FAIL, message

        else:
            message = f"{self.tap_comm_code()} : multiple measures match"
            print("WARNING", message)
            return AlignmentReportCheckStatus.WARNING, message
