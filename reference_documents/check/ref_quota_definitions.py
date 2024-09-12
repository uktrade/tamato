from reference_documents.check.base import BaseQuotaDefinitionCheck
from reference_documents.models import AlignmentReportCheckStatus


class QuotaDefinitionExists(BaseQuotaDefinitionCheck):
    name = 'Preferential Quota Exists'

    def run_check(self):
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
            if measure.duty_sentence != '':
                duty_sentences = [measure.duty_sentence]
            else:
                duty_sentences = []

            for condition in measure.conditions.latest_approved():
                if condition.duty_sentence != '':
                    duty_sentences.append(condition.duty_sentence)

            message = f"FAIL - duty rate does not match, expected {self.ref_quota_definition.duty_rate} to be in ({' or '.join(duty_sentences)})"
            return AlignmentReportCheckStatus.FAIL, message
        else:
            return AlignmentReportCheckStatus.PASS, ''



