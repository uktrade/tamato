"""
Validators for regulations
"""
from django.core.validators import RegexValidator
from django.db import models


class RoleType(models.IntegerChoices):
    """The code which indicates the role of the regulation."""

    # The integer values are hard-coded into the TARIC3 Schema

    BASE = 1, "Base"
    PROVISIONAL_ANTIDUMPING = 2, "Provisional anti-dumping"
    DEFINITIVE_ANTIDUMPING = 3, "Definitive anti-dumping"
    MODIFICATION = 4, "Modification"
    PROROGATION = 5, "Prorogation"
    COMPLETE_ABROGATION = 6, "Complete abrogation"
    EXPLICIT_ABROGATION = 7, "Explicit abrogation"
    FULL_TEMPORARY_STOP = 8, "Full temporary stop"


class ReplacementIndicator(models.IntegerChoices):
    """The code which indicates whether or not a regulation has been replaced."""

    NOT_REPLACED = 0, "Not replaced"
    REPLACED = 1, "Replaced"
    PARIIALLY_REPLACED = 2, "Partially replaced"


class CommunityCode(models.IntegerChoices):
    """Code which specifies whether the treaty origin is ECONOMIC, ATOMIC or COAL."""

    ECONOMIC = 1, "Economic"
    ATOMIC = 2, "Atomic"
    COAL = 3, "Coal"
    ECONOMIC_COAL = 4, "Economic/Coal"


# The regulation number is composed of four elements, as follows:
# - the regulation number prefix - one of the following (for EU regulations);
#     - 'C' draft regulations, decisions and agreements;
#     - 'R' regulations;
#     - 'D' decisions;
#     - 'A' agreements (accession acts which are not published as "R" or "D");
#     - 'I' Information. This means that this is not a legal act but it is used for
#         information;
#     - 'J': Judgement of the European Court of Justice.
#     or for UK regulations:
#     - 'C' Draft regulation
#     - 'P' Preferential Trade Agreement / FTA
#     - 'U' Unilateral preferences (GSP)
#     - 'S' Suspensions and reliefs
#     - 'X' Import and Export control
#     - 'N' Trade remedies
#     - 'M' MFN
#     - 'Q' Quotas
#     - 'A' Agri measures
# - the year of publication (two digits);
# - the regulation number, as published in the Official Journal (four digits); and
# - the regulation number suffix (one alphanumeric character). The suffix is used to
#     split regulations logically although they have been published as one piece of
#     legislation (for instance, for supporting different validity periods within the
#     one regulation)
regulation_id_validator = RegexValidator(
    r"""(?x)
    ((?P<prefix>C|R|D|A|I|J|P|U|S|X|N|M|Q|0)
    (?P<year>\d{2})
    (?P<number>\d{4})
    (?P<suffix>[0-9A-Z]))|
    ((?P<national_prefix>Z|V)
    (?P<national_year>\d{4})
    (?P<national_suffix>[A-Z]{3}))|
    ((?P<dummy_prefix>IYY)
    (?P<dummy_suffix>\d{5}))
"""
)

no_information_text_delimiters = RegexValidator(r"^[^|]*$", "Must not contain '|'")
