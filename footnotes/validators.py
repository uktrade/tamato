"""
Validators for footnotes
"""
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import TextChoices


class TypeChoices(TextChoices):
    """ SID choices for Footnote Types """

    TAX_TYPE = "01", "1 - UK tax type"
    VAT_RATE = "03", "3 - UK VAT rate"
    FOOTNOTES_OPLOG = "04", "4 - UK footnotes_oplog on prohibitions and restrictions"
    ADDITIONAL_NOMENCLATURE_CDD = "CA", "CA - Additional nomenclature - CADD"
    CONDITIONS = "CD", "CD - Conditions"
    CULTURAL_GOODS = "CG", "CG - Cultural goods"
    DUAL_USE_GOODS = "DU", "DU - Dual use goods"
    END_USE = "EU", "EU - End use"
    INVASIVE_ALIEN_SPECIES = "IS", "IS - Invasive alien species"
    MILITARY_GOODS_TECHNOLOGY = "MG", "MG - Military goods and technologies"
    MEURSING_TABLE = "MH", "MH - Meursing table"
    EXPORT_REFUND_MEASURE = "MX", "MX - Export refund measure"
    COMBINED_NOMENCLATURE = "NC", "NC - Combined Nomenclature"
    CN_MEASURE = "NM", "NM - CN measure"
    EXPORT_REFUND_NOMENCLATURE = "NX", "NX - Export Refund Nomenclature"
    OZONE_DEPLETING_SUBSTANCES = "OZ", "OZ - Ozone-depleting substances"
    PUBLICATION = "PB", "PB - Publication"
    SEE_ANNEX = "PN", "PN - See annex"
    TARIC_MEASURE = "TM", "TM - Taric Measure"
    TARIC_NOMENCLATURE = "TN", "TN - Taric Nomenclature"
    DYNAMIC_FOOTNOTE = "TP", "TP - Dynamic footnote"
    TORTURE_REPRESSION = "TR", "TR - Torture and repression"


FOOTNOTE_TYPE_ID_PATTERN = r"[A-Z0-9]{2}[A-Z0-9 ]?"
footnote_type_id_validator = RegexValidator(r"^" + FOOTNOTE_TYPE_ID_PATTERN + "$")

FOOTNOTE_ID_PATTERN = r"([0-9]{3}|[0-9]{5})"
footnote_id_validator = RegexValidator(r"^" + FOOTNOTE_ID_PATTERN + "$")


FootnoteIDValidator = None
FootnoteTypeIDValidator = None
