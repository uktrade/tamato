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
            message = f"Rate {self.ref_rate.commodity_code} {self.ref_rate.valid_between}: commodity code not found for period."
            print("FAIL", message)
            return AlignmentReportCheckStatus.FAIL, message

        # query measures
        measures = self.tap_related_measures()

        # this is ok - there is a single measure matching the expected query
        if len(measures) == 1:
            return AlignmentReportCheckStatus.PASS, f"{self.tap_comm_code()} {self.ref_rate.valid_between}: rate for commodity code matched"

        # this is not inline with expected measures presence - check comm code children
        elif len(measures) == 0:
            # check parents from chapter level snapshot
            parent_snapshot = self.get_snapshot(self.ref_rate.commodity_code[0:4])
            parent_commodities = []
            child_commodity = None
            match_parents = False
            match_children = False

            for commodity in parent_snapshot.commodities:
                if commodity.item_id == self.ref_rate.commodity_code and commodity.suffix == '80':
                    child_commodity = commodity
                    break

            if child_commodity is not None:
                next_parent = child_commodity
                while True:
                    next_parent = parent_snapshot.get_parent(next_parent)
                    if next_parent is None:
                        break

                    parent_commodities.append(next_parent)
                    related_measures = self.tap_related_measures(next_parent.item_id)
                    if len(related_measures) > 0:
                        match_parents = True
                        break
                    if next_parent.item_id == self.ref_rate.commodity_code[0:4] + '000000' and next_parent.suffix == '80':
                        break

            if not match_parents:
                # children recursively
                match_children = self.tap_recursive_comm_code_check(
                    self.get_snapshot(),
                    self.ref_rate.commodity_code,
                    '80',
                    1,
                )

            message = f"Rate {self.tap_comm_code()} {self.ref_rate.valid_between}: "

            if match_children:
                message += f"matched (against commodity code children)"
                print("PASS", message)

                return AlignmentReportCheckStatus.PASS, message
            if match_parents:
                message += f"matched (against commodity code parent)"
                print("PASS", message)

                return AlignmentReportCheckStatus.PASS, message
            else:
                message += f"no expected measures found on good code or children"
                print("FAIL", message)

                return AlignmentReportCheckStatus.FAIL, message

        else:
            message = f"Rate {self.tap_comm_code()} {self.ref_rate.valid_between} : multiple measures match"
            print("WARNING", message)
            return AlignmentReportCheckStatus.WARNING, message
