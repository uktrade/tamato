"""Business rules for regulations."""
import logging

from common.business_rules import BusinessRule
from common.business_rules import MustExist
from common.business_rules import PreventDeleteIfInUse
from common.business_rules import UniqueIdentifyingFields
from common.business_rules import ValidityPeriodContained
from common.business_rules import only_applicable_after

log = logging.getLogger(__name__)


class ROIMB1(UniqueIdentifyingFields):
    """The regulation id + role id must be unique."""


class ROIMB4(MustExist):
    """The referenced regulation group must exist."""

    reference_field_name = "regulation_group"


@only_applicable_after("2003-12-31")
class ROIMB8(BusinessRule):
    """Explicit dates of related measures must be within the validity period of
    the base regulation."""

    def validate(self, regulation):
        if (
            regulation.measure_set.model.objects.filter(
                generating_regulation__regulation_id=regulation.regulation_id,
                generating_regulation__role_type=regulation.role_type,
            )
            .approved_up_to_transaction(self.transaction)
            .exclude(
                valid_between__contained_by=regulation.valid_between,
            )
            .exists()
        ):
            raise self.violation(regulation)


class ROIMB44(BusinessRule):
    """
    The "Regulation Approved Flag" indicates for a draft regulation whether the
    draft is approved, i.e. the regulation is definitive apart from its
    publication (only the definitive regulation id and the O.J.

    reference are not yet known).  A draft regulation (regulation id starts with
    a 'C') can have its "Regulation Approved Flag" set to 0='Not Approved' or
    1='Approved'. Its flag can only change from 0='Not Approved' to
    1='Approved'. Any other regulation must have its "Regulation Approved Flag"
    set to 1='Approved'.
    """

    # We need to work on the draft –> live status however, as we have not yet worked
    # this through

    def validate(self, regulation):
        if regulation.is_draft_regulation and not regulation.approved:
            if (
                type(regulation)
                .objects.filter(
                    **regulation.get_identifying_fields(),
                    approved=True,
                )
                .exclude(pk=regulation.pk)
                .exists()
            ):
                raise self.violation(
                    model=regulation,
                    message=(
                        "A draft regulation can only have its 'Regulation Approved "
                        "Flag' change from 'Not Approved' to 'Approved'."
                    ),
                )

        elif not regulation.approved:
            raise self.violation(
                model=regulation,
                message=(
                    "A non-draft regulation must have its 'Regulation Approved Flag' "
                    "set to 'Approved'."
                ),
            )


class ROIMB46(PreventDeleteIfInUse):
    """A base regulation cannot be deleted if it is used as a justification
    regulation, except for ‘C’ regulations used only in measures as both
    measure-generating regulation and justification regulation."""

    # We should not be deleting base regulations. Also, we will not be using the
    # justification regulation field, though there will be a lot of EU regulations where
    # the justification regulation field is set.

    in_use_check = (
        "used_as_terminating_regulation_or_draft_generating_and_terminating_regulation"
    )


class ROIMB47(ValidityPeriodContained):
    """The validity period of the regulation group id must span the validity
    period of the base regulation."""

    # But we will be ensuring that the regulation groups are not end dated, therefore we
    # will not get hit by this

    container_field_name = "regulation_group"
