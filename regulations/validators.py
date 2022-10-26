"""Validators for regulations."""
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
    """The code which indicates whether or not a regulation has been
    replaced."""

    NOT_REPLACED = 0, "Not replaced"
    REPLACED = 1, "Replaced"
    PARIIALLY_REPLACED = 2, "Partially replaced"


class CommunityCode(models.IntegerChoices):
    """Code which specifies whether the treaty origin is ECONOMIC, ATOMIC or
    COAL."""

    ECONOMIC = 1, "Economic"
    ATOMIC = 2, "Atomic"
    COAL = 3, "Coal"
    ECONOMIC_COAL = 4, "Economic/Coal"


class RegulationUsage(models.TextChoices):
    __empty__ = "Select a regulation usage"
    DRAFT_REGULATION = "C", "C: Draft regulation"
    PREFERENTIAL_TRADE_AGREEMENT = "P", "P: Preferential Trade Agreement / FTA"
    UNILATERAL_PREFERENCES = "U", "U: Unilateral preferences (GSP)"
    SUSPENSIONS_AND_RELIEFS = "S", "S: Suspensions and reliefs"
    IMPORT_AND_EXPORT_CONTROL = "X", "X: Import and Export control"
    TRADE_REMEDIES = "N", "N: Trade remedies"
    MFN = "M", "M:  MFN"
    QUOTAS = "Q", "Q: Quotas"
    AGRI_MEASURES = "A", "A: Agri measures"


UK_ID_PREFIXES = "".join([ru for ru in RegulationUsage.values if ru is not None])

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
TARIC_ID = (
    r"([CRDAIJ])"  # regulation usage.
    r"(\d{2})"  # publication year.
    r"(\d{4})"  # regulation sequence number.
    r"([0-9A-Z])"  # suffix.
)
UK_ID = (
    rf"([{UK_ID_PREFIXES}])"  # regulation usage.
    r"(\d{2})"  # publication year.
    r"(\d{4})"  # regulation sequence number.
    r"([0-9A-Z])"  # suffix.
)
NATIONAL_ID = r"([ZV])" r"(\d{4})" r"([A-Z]{3})"
DUMMY_ID = r"IYY\d{5}"
REGULATION_ID_REGEX = rf"({TARIC_ID}|{UK_ID}|{NATIONAL_ID}|{DUMMY_ID})"
regulation_id_validator = RegexValidator(rf"^{REGULATION_ID_REGEX}$")


no_information_text_delimiters = RegexValidator(
    r"^[^|\xA0]*$",
    "Must not contain '|' or 0xA0",
)
