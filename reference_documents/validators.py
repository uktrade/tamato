from django.core.validators import RegexValidator

commodity_code_validator = RegexValidator(r"\d{10}")
