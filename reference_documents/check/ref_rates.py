from reference_documents.check.base import BaseRateCheck
from reference_documents.models import AlignmentReportCheckStatus


class RateExists(BaseRateCheck):
    name = 'rate exists'

    def run_check(self):
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

            message = f"{self.tap_comm_code()}, {self.tap_geo_area_description()}"

            if match:
                message += f"\nmatched with children"
                print("PASS", message)

                return AlignmentReportCheckStatus.PASS, message
            else:
                message += f"\nno expected measures found on good code or children"
                print("FAIL", message)

                return AlignmentReportCheckStatus.FAIL, message

        elif len(measures) > 1:
            message = f"multiple measures match {self.tap_comm_code()}, {self.tap_geo_area_description()}"
            print("WARNING", message)
            return AlignmentReportCheckStatus.WARNING, message

        else:
            return AlignmentReportCheckStatus.PASS, ''
