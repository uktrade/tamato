from django.core.validators import RegexValidator


EnvelopeIdValidator = RegexValidator(r"^(?P<year>\d\d)(?P<counter>\d{4})$")
