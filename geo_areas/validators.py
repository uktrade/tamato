from django.core.validators import RegexValidator
from django.db import models


AREA_ID_REGEX = r"^[A-Z0-9]{2}$|^[A-Z0-9]{4}$"

area_id_validator = RegexValidator(AREA_ID_REGEX)


class AreaCode(models.IntegerChoices):
    COUNTRY = 0, "Country"
    GROUP = 1, "Geographical Area Group"
    REGION = 2, "Region"
