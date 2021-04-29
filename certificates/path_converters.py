"""Custom path converters for certificates
https://docs.djangoproject.com/en/3.2/topics/http/urls/#registering-custom-path-
converters."""

from django.urls.converters import StringConverter

from certificates import validators


class CertificateTypeSIDConverter(StringConverter):
    regex = validators.CERTIFICATE_TYPE_SID_REGEX


class CertificateSIDConverter(StringConverter):
    regex = validators.CERTIFICATE_SID_REGEX
