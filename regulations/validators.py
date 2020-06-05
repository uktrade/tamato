"""
Validators for regulations
"""
import re

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator


class RegulationIDValidator(RegexValidator):
    """The regulation number is composed of four elements, as follows:
    - the regulation number prefix - one of the following (for EU regulations);
        - 'C' draft regulations, decisions and agreements;
        - 'R' regulations;
        - 'D' decisions;
        - 'A' agreements (accession acts which are not published as "R" or "D");
        - 'I' Information. This means that this is not a legal act but it is used for
          information;
        - 'J': Judgement of the European Court of Justice.
      or for UK regulations:
        - 'C' Draft regulation
        - 'P' Preferential Trade Agreement / FTA
        - 'U' Unilateral preferences (GSP)
        - 'S' Suspensions and reliefs
        - 'X' Import and Export control
        - 'N' Trade remedies
        - 'M' MFN
        - 'Q' Quotas
        - 'A' Agri measures
    - the year of publication (two digits);
    - the regulation number, as published in the Official Journal (four digits); and
    - the regulation number suffix (one alphanumeric character). The suffix is used to
      split regulations logically although they have been published as one piece of
      legislation (for instance, for supporting different validity periods within the
      one regulation)
    """

    def __init__(self, *args, **kwargs):
        super().__init__(
            r"""(?x)
            (?P<prefix>C|R|D|A|I|J|P|U|S|X|N|M|Q)
            (?P<year>\d{2})
            (?P<number>\d{4})
            (?P<suffix>[0-9A-Z])
            """
        )


def validate_approved(regulation):
    """ROIMB44

    A draft regulation (regulation id starts with a 'C') can have its "Regulation
    Approved Flag" set to 0='Not Approved' or 1='Approved'.  Any other regulation must
    have its "Regulation Approved Flag" set to 1='Approved'.
    """

    if not regulation.is_draft_regulation and not regulation.approved:
        raise ValidationError("Only draft regulations can be 'Not Approved'")


def can_change_approved(regulation):
    """ROIMB44

    (A draft regulation's) flag can only change from 0='Not Approved' to 1='Approved'.
    """

    return regulation.is_draft_regulation and not regulation.approved


def validate_official_journal(regulation):
    """Official Journal number and page must both be set, or must both be NULL"""

    return bool(regulation.official_journal_number) == bool(official_journal_page)


def unique_regulation_id_for_role_type(regulation):
    """ROIMB1

    The (regulation id + role id) must be unique.
    """

    Regulation = regulation.__class__
    # TODO depends on TrackedModel and Workbasket implementation
    # existing = Regulation.live_objects.filter(
    #     regulation_id=regulation.regulation_id,
    #     role_type=regulation.role_type,
    # )
    existing = Regulation.objects.filter(
        regulation_id=regulation.regulation_id, role_type=regulation.role_type
    )
    if regulation.id:
        existing = existing.exclude(id=regulation.id)
    if len(existing) > 0:
        raise ValidationError("The (regulation id + role id) must be unique.")
