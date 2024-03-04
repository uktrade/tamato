from django.core.validators import RegexValidator

commodity_code_validator = RegexValidator(r"\d{10}")
order_number_validator = RegexValidator(r"^05[0-9]{4}$")
