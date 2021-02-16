"""Validators for footnotes."""
from django.core.validators import RegexValidator
from django.db import models


# Footnote type application codes
class ApplicationCode(models.IntegerChoices):
    CN_NOMENCLATURE = 1, "CN nomenclature"
    TARIC_NOMENCLATURE = 2, "TARIC nomenclature"
    EXPORT_REFUND_NOMENCLATURE = 3, "Export refund nomenclature"
    WINE_REFERENCE_NOMENCLATURE = 4, "Wine reference nomenclature"
    ADDITIONAL_CODES = 5, "Additional codes"
    CN_MEASURES = 6, "CN measures"
    OTHER_MEASURES = 7, "Other measures"
    MEURSING_HEADING = 8, "Meursing Heading"
    DYNAMIC_FOOTNOTE = 9, "Dynamic footnote"


FOOTNOTE_TYPE_ID_PATTERN = r"[A-Z0-9]{2}[A-Z0-9 ]?"
footnote_type_id_validator = RegexValidator(r"^" + FOOTNOTE_TYPE_ID_PATTERN + "$")

FOOTNOTE_ID_PATTERN = r"([0-9]{3}|[0-9]{5})"
footnote_id_validator = RegexValidator(r"^" + FOOTNOTE_ID_PATTERN + "$")


FootnoteIDValidator = None
FootnoteTypeIDValidator = None
