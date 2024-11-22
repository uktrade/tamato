from reference_documents.check.base import BaseQuotaDefinitionCheck
from reference_documents.models import AlignmentReportCheckStatus


class QuotaDefinitionChecks(BaseQuotaDefinitionCheck):
    """Class defining the check process for a reference document quota
    definition (RefQuotaDefinition)"""

    name = "Quota definition checks"

    def run_check(self):
        """
        Runs quota definition checks between a reference document defined quota
        definition and TAP data.

        Returns:
            AlignmentReportCheckStatus: status based on the result of the check (pass, warning, fail, skip)
            string: corresponding message for the status.
        """
        if not self.commodity_code():
            message = f"FAIL - commodity code not found"
            return AlignmentReportCheckStatus.FAIL, message

        elif not self.quota_definition():
            message = f"FAIL - quota definition not found"
            return AlignmentReportCheckStatus.FAIL, message

        elif not self.measures():
            message = (
                f"FAIL - measure(s) spanning whole quota definition period not found"
            )
            return AlignmentReportCheckStatus.FAIL, message

        elif not self.duty_rate_matches():
            measure = self.measures().first()

            # get all duty sentences
            if measure.duty_sentence != "":
                duty_sentences = [measure.duty_sentence]
            else:
                duty_sentences = []

            for condition in measure.conditions.latest_approved():
                if condition.duty_sentence != "":
                    duty_sentences.append(condition.duty_sentence)

            message = f"FAIL - duty rate does not match, expected {self.ref_quota_definition.duty_rate} to be in ({' or '.join(duty_sentences)})"
            return AlignmentReportCheckStatus.FAIL, message
        else:
            return AlignmentReportCheckStatus.PASS, ""
